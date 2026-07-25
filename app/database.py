import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with sqlite3.connect(settings.db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tg_user_id INTEGER UNIQUE NOT NULL,
              full_name TEXT,
              email TEXT,
              phone TEXT,
              role TEXT NOT NULL DEFAULT 'guest',
              onboarding_stage TEXT NOT NULL DEFAULT 'new',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              description TEXT,
              event_type TEXT NOT NULL DEFAULT 'open',
              format_type TEXT NOT NULL DEFAULT 'offline',
              starts_at TEXT NOT NULL,
              location TEXT,
              seats_limit INTEGER NOT NULL DEFAULT 0,
              guest_price_uah INTEGER NOT NULL DEFAULT 0,
              member_price_uah INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'upcoming'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              event_id INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending_payment',
              amount_uah INTEGER NOT NULL DEFAULT 0,
              wayforpay_order_reference TEXT,
              payment_status TEXT NOT NULL DEFAULT 'none',
              attended INTEGER NOT NULL DEFAULT 0,
              feedback_sent INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE (user_id, event_id)
            )
            """
        )
        # Backward compatibility:
        # Якщо в старій БД був унікальний індекс тільки на user_id, це обмежує
        # реєстрацію одним заходом на користувача. Видаляємо та гарантуємо
        # унікальність тільки пари (user_id, event_id).
        try:
            idx_rows = cur.execute("PRAGMA index_list('registrations')").fetchall()
            for idx in idx_rows:
                # pragma index_list: (seq, name, unique, origin, partial)
                idx_name = idx[1]
                is_unique = int(idx[2]) == 1
                if not is_unique:
                    continue
                cols = cur.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
                col_names = [c[2] for c in cols]
                if col_names == ["user_id"]:
                    cur.execute(f'DROP INDEX IF EXISTS "{idx_name}"')
        except Exception:
            pass
        try:
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_registrations_user_event ON registrations(user_id, event_id)")
        except Exception:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              event_id INTEGER,
              stage TEXT NOT NULL,
              run_at TEXT NOT NULL,
              attempts INTEGER NOT NULL DEFAULT 0,
              max_attempts INTEGER NOT NULL DEFAULT 3,
              status TEXT NOT NULL DEFAULT 'scheduled',
              message_text TEXT NOT NULL
            )
            """
        )
        try:
            cur.execute("ALTER TABLE registrations ADD COLUMN attended INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE registrations ADD COLUMN feedback_sent INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        for col, ctype in [
            ("rsvp_will_attend", "INTEGER"),
            ("reminder_rsvp_40h_sent", "INTEGER NOT NULL DEFAULT 0"),
            ("reminder_24h_sent", "INTEGER NOT NULL DEFAULT 0"),
            ("reminder_3h_sent", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                cur.execute(f"ALTER TABLE registrations ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN tg_username TEXT")
        except sqlite3.OperationalError:
            pass
        for col, ctype in [
            ("membership_expires_at", "TEXT"),
            ("membership_period", "TEXT"),
            ("membership_amount_uah", "INTEGER DEFAULT 0"),
            ("membership_payment_url", "TEXT"),
            ("pending_deeplink_event_id", "INTEGER"),
            ("deeplink_source", "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass
        for col, ctype in [
            ("banner_url", "TEXT"),
            ("zoom_url", "TEXT"),
            ("lead_price_uah", "INTEGER"),
            ("wayforpay_guest_url", "TEXT"),
            ("wayforpay_lead_url", "TEXT"),
            ("wayforpay_member_url", "TEXT"),
            ("guest_discount_price_uah", "INTEGER"),
            ("lead_discount_price_uah", "INTEGER"),
            ("member_discount_price_uah", "INTEGER"),
            ("admin_digest_24h_sent", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                cur.execute(f"ALTER TABLE events ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass
        for col, ctype in [
            ("msg_rsvp_40h", "TEXT"),
            ("msg_remind_24h", "TEXT"),
            ("msg_remind_3h", "TEXT"),
            ("waitlist_enabled", "INTEGER NOT NULL DEFAULT 1"),
        ]:
            try:
                cur.execute(f"ALTER TABLE events ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass
        try:
            cur.execute("ALTER TABLE registrations ADD COLUMN no_show INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS event_waitlist (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              event_id INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              notified_at TEXT,
              UNIQUE (user_id, event_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              kind TEXT NOT NULL,
              user_id INTEGER,
              event_id INTEGER,
              detail TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT)
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS support_threads (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              status TEXT NOT NULL DEFAULT 'open',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS support_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              thread_id INTEGER NOT NULL,
              from_admin INTEGER NOT NULL DEFAULT 0,
              content TEXT NOT NULL,
              content_type TEXT NOT NULL DEFAULT 'text',
              created_at TEXT NOT NULL,
              FOREIGN KEY (thread_id) REFERENCES support_threads(id)
            )
            """
        )
        cur.execute("UPDATE support_threads SET status = 'archived' WHERE status = 'closed'")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS membership_settings (
              period TEXT PRIMARY KEY,
              months INTEGER NOT NULL,
              amount_uah INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS membership_payments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              wayforpay_order_reference TEXT UNIQUE,
              amount_uah INTEGER NOT NULL,
              period TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              created_at TEXT NOT NULL
            )
            """
        )
        for row in [("month", 1, 100), ("quarter", 3, 270), ("year", 12, 1000)]:
            cur.execute("INSERT OR IGNORE INTO membership_settings (period, months, amount_uah) VALUES (?, ?, ?)", row)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              event_id INTEGER NOT NULL,
              rating INTEGER,
              review_text TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_pending (
              user_id INTEGER PRIMARY KEY,
              event_id INTEGER NOT NULL,
              stage TEXT NOT NULL DEFAULT 'waiting_rating'
            )
            """
        )
        for col, ctype in [
            ("created_at", "TEXT"),
            ("nudge_sent", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                cur.execute(f"ALTER TABLE feedback_pending ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS member_applications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              motivation TEXT,
              experience TEXT,
              created_at TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS member_application_pending (
              user_id INTEGER PRIMARY KEY,
              stage TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS member_tags (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_tags (
              user_id INTEGER NOT NULL,
              tag_id INTEGER NOT NULL,
              PRIMARY KEY (user_id, tag_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reminder_settings (
              stage TEXT PRIMARY KEY,
              stage_name TEXT,
              message_text TEXT NOT NULL,
              delay_minutes INTEGER NOT NULL DEFAULT 60,
              max_attempts INTEGER NOT NULL DEFAULT 3,
              enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        for col, ctype in [
            ("stage_name", "TEXT"),
            ("max_attempts", "INTEGER NOT NULL DEFAULT 3"),
            ("enabled", "INTEGER NOT NULL DEFAULT 1"),
        ]:
            try:
                cur.execute(f"ALTER TABLE reminder_settings ADD COLUMN {col} {ctype}")
            except sqlite3.OperationalError:
                pass
        # Seed default reminder settings for funnel stages
        defaults = [
            ("stage_1", "Почав реєстрацію, не ввів дані", "Ви почали реєстрацію, але ще не завершили її. Продовжимо?", 60, 1, 1),
            ("stage_2", "Ввів дані, не обрав захід", "Ви завершили реєстрацію! Оберіть захід з розділу «Події».", 120, 1, 1),
            ("stage_3", "Обрав захід, не перейшов до оплати", "Ви обрали захід. Завершіть оплату.", 60, 1, 1),
            ("stage_4", "Перейшов до оплати, не завершив", "Оплата не завершена. Натисніть «Події» і повторіть спробу.", 120, 1, 1),
            ("stage_5", "Оплатив — нагадування перед подією", "Нагадуємо: подія відбудеться незабаром! Не пропустіть.", 1440, 1, 1),
        ]
        for stage, name, msg, delay, max_a, en in defaults:
            cur.execute(
                """INSERT OR IGNORE INTO reminder_settings (stage, stage_name, message_text, delay_minutes, max_attempts, enabled)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (stage, name, msg, delay, max_a, en),
            )
        cur.execute(
            """INSERT OR IGNORE INTO reminder_settings (stage, stage_name, message_text, delay_minutes, max_attempts, enabled)
            VALUES ('stage_4_unpaid_1h', 'Оплата події — 1 год', 'Ви не завершили оплату за захід. Натисніть, щоб отримати посилання на оплату.', 60, 1, 1)"""
        )
        cur.execute(
            """INSERT OR IGNORE INTO reminder_settings (stage, stage_name, message_text, delay_minutes, max_attempts, enabled)
            VALUES ('stage_4_unpaid_24h', 'Оплата події — 24 год', 'Ви не завершили оплату за захід. Завершіть оплату, щоб зберегти місце.', 1440, 1, 1)"""
        )
        # Роль lead: незавершений онбординг (окрім member/admin)
        try:
            cur.execute(
                """UPDATE users SET role = 'lead' WHERE (onboarding_stage IS NULL OR onboarding_stage != 'done')
                AND role NOT IN ('member', 'admin')"""
            )
        except sqlite3.OperationalError:
            pass
        # Дефолти для шаблонів таймлайну та тихих годин (перезапис не робимо — лише якщо порожньо)
        cfg_defaults = [
            ("default_msg_rsvp_40h", "Нагадування: подія «{title}» ({datetime}). Підтвердіть, чи будете присутні?"),
            ("default_msg_remind_24h", "Нагадування (за добу): «{title}»\n📅 {datetime}\n📍 {location}\n🔗 {zoom}\nЩо взяти з собою: за потреби нотатник, вода."),
            ("default_msg_remind_3h", "Через кілька годин: «{title}» ({datetime})."),
            ("timeline_rsvp_40_enabled", "1"),
            ("timeline_24h_enabled", "1"),
            ("timeline_3h_enabled", "1"),
            ("quiet_hours_enabled", "0"),
            ("quiet_hours_start", "22"),
            ("quiet_hours_end", "8"),
            ("quiet_hours_tz", "Europe/Kyiv"),
        ]
        for k, v in cfg_defaults:
            cur.execute("INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)", (k, v))
        conn.commit()


@contextmanager
def db():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
