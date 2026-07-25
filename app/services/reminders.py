from datetime import datetime, timedelta, timezone

from app.database import db


def has_sent_reminder(user_id: int, stage: str, event_id: int | None = None) -> bool:
    """Перевіряє, чи вже надсилалось або заплановано нагадування (щоб не спамити)."""
    with db() as conn:
        q = "SELECT 1 FROM reminders WHERE user_id = ? AND stage = ? AND status IN ('sent', 'scheduled')"
        params: list = [user_id, stage]
        if event_id is not None and stage in ("stage_4", "stage_5", "stage_4_unpaid_24h", "stage_4_unpaid_1h"):
            q += " AND event_id = ?"
            params.append(event_id)
        else:
            q += " AND event_id IS NULL"
        q += " LIMIT 1"
        return conn.execute(q, params).fetchone() is not None


def get_reminder_settings(stage: str) -> dict | None:
    """Повертає налаштування для етапу або None."""
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM reminder_settings WHERE stage = ? AND enabled = 1",
            (stage,),
        ).fetchone()
        return dict(row) if row else None


def schedule_reminder(
    user_id: int,
    stage: str,
    message_text: str | None = None,
    minutes_from_now: int | None = None,
    event_id: int | None = None,
) -> None:
    """Планує нагадування. Не планує, якщо вже надсилалось (щоб не спамити)."""
    if has_sent_reminder(user_id, stage, event_id):
        return
    settings_row = get_reminder_settings(stage)
    if settings_row:
        msg = message_text or settings_row.get("message_text", "")
        mins = minutes_from_now if minutes_from_now is not None else settings_row.get("delay_minutes", 60)
        max_attempts = settings_row.get("max_attempts", 3)
    else:
        msg = message_text or "Нагадування"
        mins = minutes_from_now or 60
        max_attempts = 3
    run_at = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO reminders (user_id, event_id, stage, run_at, message_text, max_attempts)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, event_id or None, stage, run_at, msg, max_attempts),
        )


def schedule_event_reminder(user_id: int, event_id: int) -> None:
    """Планує нагадування перед подією (stage_5) для оплатившого користувача."""
    if has_sent_reminder(user_id, "stage_5", event_id):
        return
    settings_row = get_reminder_settings("stage_5")
    if not settings_row:
        return
    with db() as conn:
        ev = conn.execute("SELECT starts_at FROM events WHERE id = ?", (event_id,)).fetchone()
        if not ev:
            return
    try:
        starts = datetime.fromisoformat(ev["starts_at"].replace("Z", "+00:00"))
    except Exception:
        return
    delay_min = settings_row.get("delay_minutes", 1440)
    run_at = (starts - timedelta(minutes=delay_min)).isoformat()
    msg = settings_row.get("message_text", "Нагадуємо: подія відбудеться незабаром!")
    with db() as conn:
        conn.execute(
            """
            INSERT INTO reminders (user_id, event_id, stage, run_at, message_text, max_attempts)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, event_id, "stage_5", run_at, msg, settings_row.get("max_attempts", 1)),
        )


def due_reminders(limit: int = 50):
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        rows = conn.execute(
            """
            SELECT r.*, u.tg_user_id, u.email, u.phone, u.full_name
            FROM reminders r
            JOIN users u ON u.id = r.user_id
            WHERE r.status = 'scheduled' AND r.run_at <= ?
            ORDER BY r.run_at ASC
            LIMIT ?
            """,
            (now, limit),
        ).fetchall()
        return rows


def get_registration(user_id: int, event_id: int):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM registrations WHERE user_id = ? AND event_id = ?",
            (user_id, event_id),
        ).fetchone()


def mark_sent(reminder_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE reminders SET status = 'sent' WHERE id = ?", (reminder_id,))
