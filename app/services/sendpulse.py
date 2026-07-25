"""
SendPulse integration: sync users to addressbook (CRM-style contact storage).
Auth: SENDPULSE_API_KEY (Bearer) або SENDPULSE_CLIENT_ID + SENDPULSE_CLIENT_SECRET (OAuth).
"""
import httpx

from app.config import settings


async def _get_token() -> str | None:
    """Отримати Bearer token: API key або OAuth."""
    if getattr(settings, "sendpulse_api_key", None):
        return settings.sendpulse_api_key
    cid = getattr(settings, "sendpulse_client_id", None) or ""
    csec = getattr(settings, "sendpulse_client_secret", None) or ""
    if not cid or not csec:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.sendpulse.com/oauth/access_token",
            json={"grant_type": "client_credentials", "client_id": cid, "client_secret": csec},
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("access_token")
    return None


def _headers() -> dict:
    return {"Content-Type": "application/json"}


async def upsert_contact(contact: dict) -> bool:
    """
    Add/update contact in SendPulse addressbook.
    contact: { email, full_name, phone, role, telegram_id, tg_username, external_id, event_ids, payment_status, opys, tag_ids }
    opys: опис (мотивація, досвід тощо)
    tag_ids: список ID тегів (напр. для "зв'язатись" коли людина кинула питання)
    """
    token = await _get_token()
    if not token:
        return False
    book_id = settings.sendpulse_addressbook_id
    if not book_id:
        book_id = await _ensure_addressbook(token)
    if not book_id:
        return False

    email = (contact.get("email") or "").strip()
    if not email:
        email = f"tg_{contact.get('telegram_id', '')}@placeholder.bot"

    variables = {
        "Name": str(contact.get("full_name") or "")[:254],
        "Phone": str(contact.get("phone") or ""),
        "role": str(contact.get("role") or "guest"),
        "telegram_id": str(contact.get("telegram_id") or ""),
        "telegram_username": str(contact.get("tg_username") or ""),
        "external_id": str(contact.get("external_id") or ""),
        "payment_status": str(contact.get("payment_status") or ""),
        "event_ids": str(contact.get("event_ids") or "")[:254],
        "opys": str(contact.get("opys") or "")[:500],
    }

    payload = {
        "emails": [{"email": email, "variables": variables}]
    }
    tag_ids = contact.get("tag_ids") or []
    if tag_ids:
        payload["tags"] = tag_ids
    headers = {**_headers(), "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            f"https://api.sendpulse.com/addressbooks/{book_id}/emails",
            headers=headers,
            json=payload,
        )
        if r.status_code not in (200, 201):
            try:
                err = r.json()
                print(f"[SendPulse] Помилка {r.status_code}: {err}")
            except Exception:
                print(f"[SendPulse] Помилка {r.status_code}: {r.text}")
            return False
        return True


_cached_book_id: str | None = None


async def _ensure_addressbook(token: str) -> str | None:
    """Get or create default addressbook, return its ID."""
    global _cached_book_id
    if _cached_book_id:
        return _cached_book_id
    headers = {**_headers(), "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://api.sendpulse.com/addressbooks", headers=headers)
        if r.status_code == 200:
            try:
                books = r.json()
                if not isinstance(books, list):
                    books = []
                for b in books:
                    if b.get("name") == "Community Bot Contacts":
                        _cached_book_id = str(b["id"])
                        return _cached_book_id
            except Exception as e:
                print(f"[SendPulse] Помилка парсингу списку: {e}")
        r = await client.post(
            "https://api.sendpulse.com/addressbooks",
            headers=headers,
            json={"bookName": "Community Bot Contacts"},
        )
        if r.status_code in (200, 201):
            try:
                data = r.json()
                _cached_book_id = str(data.get("id", ""))
                return _cached_book_id
            except Exception as e:
                print(f"[SendPulse] Помилка створення книги: {e}")
        else:
            print(f"[SendPulse] create addressbook: {r.status_code} {r.text}")
    return None
