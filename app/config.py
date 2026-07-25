import os
import re
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass


def _getenv(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    app_base_url: str = _getenv("APP_BASE_URL", "http://localhost:8000")
    admin_public_url: str = _getenv("ADMIN_PUBLIC_URL", "").strip() or _getenv("APP_BASE_URL", "http://localhost:8000")
    app_env: str = _getenv("APP_ENV", "dev")
    app_secret_key: str = _getenv("APP_SECRET_KEY", "change_me")
    db_path: str = _getenv("DB_PATH", "./bot.db")

    telegram_bot_token: str = _getenv("TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str = _getenv("TELEGRAM_WEBHOOK_SECRET", "replace_me")
    admin_telegram_ids: str = _getenv("ADMIN_TELEGRAM_IDS", "")
    use_polling: bool = _getenv("USE_POLLING", "true").lower() in ("1", "true", "yes")

    wayforpay_merchant_login: str = _getenv("WAYFORPAY_MERCHANT_LOGIN")
    wayforpay_secret_key: str = _getenv("WAYFORPAY_SECRET_KEY")
    wayforpay_return_url: str = _getenv("WAYFORPAY_RETURN_URL", "http://localhost:8000/pay/return")
    wayforpay_service_url: str = _getenv("WAYFORPAY_SERVICE_URL", "http://localhost:8000/wayforpay/callback")
    wayforpay_membership_url: str = _getenv("WAYFORPAY_MEMBERSHIP_URL", "")
    wayforpay_event_guest_url: str = _getenv("WAYFORPAY_EVENT_GUEST_URL", "")
    wayforpay_event_member_url: str = _getenv("WAYFORPAY_EVENT_MEMBER_URL", "")

    sendpulse_api_key: str = _getenv("SENDPULSE_API_KEY")
    sendpulse_client_id: str = _getenv("SENDPULSE_CLIENT_ID", "")
    sendpulse_client_secret: str = _getenv("SENDPULSE_CLIENT_SECRET", "")
    sendpulse_addressbook_id: str = _getenv("SENDPULSE_ADDRESSBOOK_ID", "")
    sendpulse_tag_contact_me: str = _getenv("SENDPULSE_TAG_CONTACT_ME", "")  # ID тегу «Потрібно зв'язатись»

    @property
    def telegram_api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.telegram_bot_token}"

    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_telegram_ids:
            return set()
        return {int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()}

    @property
    def admin_support_notify_chat_id(self) -> int:
        """Група/канал Telegram для сповіщень про нові звернення в підтримку (ADMIN_SUPPORT_NOTIFY_CHAT_ID)."""
        raw = _getenv("ADMIN_SUPPORT_NOTIFY_CHAT_ID", "")
        if not raw:
            return 0
        # Підтримка форматів: -100123..., -100123...:12, -100123.../12
        m = re.match(r"^\s*(-?\d+)", raw)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return 0
        try:
            return int(raw)
        except ValueError:
            return 0

    @property
    def admin_support_notify_thread_id(self) -> int:
        """Topic id для forum-групи (опційно): ADMIN_SUPPORT_NOTIFY_CHAT_ID=-100...:12."""
        raw = _getenv("ADMIN_SUPPORT_NOTIFY_CHAT_ID", "")
        if not raw:
            return 0
        m = re.match(r"^\s*-?\d+\s*[:/|]\s*(\d+)", raw)
        if not m:
            return 0
        try:
            return int(m.group(1))
        except ValueError:
            return 0


settings = Settings()
