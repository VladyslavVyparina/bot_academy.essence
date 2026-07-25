import httpx

from app.config import settings


async def delete_webhook() -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{settings.telegram_api_base}/deleteWebhook")
        return r.status_code == 200 and r.json().get("ok")


async def get_updates(offset: int | None = None, timeout: int = 30) -> list:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    async with httpx.AsyncClient(timeout=timeout + 5) as client:
        r = await client.get(f"{settings.telegram_api_base}/getUpdates", params=params)
        data = r.json() if r.status_code == 200 else {}
        return data.get("result", [])


async def answer_callback(callback_query_id: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{settings.telegram_api_base}/answerCallbackQuery", json={"callback_query_id": callback_query_id})


async def send_photo(chat_id: int, photo_url: str, caption: str = "", reply_markup: dict | None = None) -> bool:
    """Відправити фото по URL."""
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption[:1024]
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{settings.telegram_api_base}/sendPhoto", json=payload)
        return r.status_code == 200


async def send_video(chat_id: int, video_url: str, caption: str = "", reply_markup: dict | None = None) -> bool:
    """Відправити відео по URL."""
    payload = {"chat_id": chat_id, "video": video_url}
    if caption:
        payload["caption"] = caption[:1024]
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{settings.telegram_api_base}/sendVideo", json=payload)
        return r.status_code == 200


async def send_document(chat_id: int, document_url: str, caption: str = "", reply_markup: dict | None = None) -> bool:
    """Відправити документ/файл по URL."""
    payload = {"chat_id": chat_id, "document": document_url}
    if caption:
        payload["caption"] = caption[:1024]
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{settings.telegram_api_base}/sendDocument", json=payload)
        return r.status_code == 200


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
    parse_mode: str | None = None,
    return_message_id: bool = False,
    message_thread_id: int | None = None,
) -> bool | int | None:
    if not (text or "").strip():
        print("[BOT] send_message: пропущено (порожній текст)")
        return None if return_message_id else False
    payload = {"chat_id": chat_id, "text": (text or "").strip()}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if message_thread_id:
        payload["message_thread_id"] = int(message_thread_id)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{settings.telegram_api_base}/sendMessage", json=payload)
        if r.status_code != 200:
            try:
                err = r.json()
                print(f"[BOT] sendMessage помилка {r.status_code}: {err}")
            except Exception:
                print(f"[BOT] sendMessage помилка {r.status_code}: {r.text}")
            return None if return_message_id else False
        if return_message_id:
            try:
                return r.json().get("result", {}).get("message_id")
            except Exception:
                return None
        return True


async def delete_message(chat_id: int, message_id: int) -> bool:
    """Видалити повідомлення бота з чату."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{settings.telegram_api_base}/deleteMessage",
            json={"chat_id": chat_id, "message_id": message_id},
        )
        return r.status_code == 200


async def edit_message_text(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None, parse_mode: str | None = None) -> bool:
    """Оновити текст повідомлення (попереднє меню зникає)."""
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(f"{settings.telegram_api_base}/editMessageText", json=payload)
        return r.status_code == 200


def inline_url_button(text: str, url: str) -> dict:
    return {"inline_keyboard": [[{"text": text, "url": url}]]}


def inline_keyboard(buttons: list[list[dict]]) -> dict:
    """buttons: [[{text, callback_data}], ...]"""
    return {"inline_keyboard": buttons}


def main_inline_menu(role: str) -> list:
    """Inline меню головне з кнопкою Назад (для вкладених екранів)."""
    info_row = [
        {"text": "ℹ️ Про академію", "callback_data": "menu_about"},
        {"text": "📄 Політика", "callback_data": "menu_policy"},
    ]
    contact_row = [{"text": "💬 Менеджер", "callback_data": "menu_manager"}]
    if role == "member":
        return [
            [{"text": "📅 Події", "callback_data": "menu_events"}, {"text": "🏠 Мій кабінет", "callback_data": "menu_cabinet"}],
            [{"text": "👤 Моя картка", "callback_data": "menu_mycard"}, {"text": "👥 Картки учасників", "callback_data": "menu_cards"}],
            info_row,
            contact_row,
            [{"text": "❓ Питання адміну", "callback_data": "menu_support"}],
        ]
    return [
        [{"text": "📅 Події", "callback_data": "menu_events"}, {"text": "🏠 Мій кабінет", "callback_data": "menu_cabinet"}],
        info_row,
        [{"text": "👤 Стати учасником", "callback_data": "menu_apply"}],
        contact_row,
        [{"text": "❓ Питання адміну", "callback_data": "menu_support"}],
    ]


def back_button(target: str = "main") -> list:
    return [[{"text": "↩️ Назад", "callback_data": f"back_{target}"}]]


def main_menu_keyboard(role: str) -> dict:
    if role == "member":
        return {
            "keyboard": [
                [{"text": "📅 Події"}, {"text": "🏠 Мій кабінет"}],
                [{"text": "👤 Моя картка"}, {"text": "👥 Картки учасників"}],
                [{"text": "ℹ️ Про академію"}, {"text": "📄 Політика / оферта"}],
                [{"text": "💬 Менеджер"}, {"text": "❓ Питання адміну"}],
            ],
            "resize_keyboard": True,
        }
    return {
        "keyboard": [
            [{"text": "📅 Події"}, {"text": "🏠 Мій кабінет"}],
            [{"text": "ℹ️ Про академію"}, {"text": "📄 Політика / оферта"}],
            [{"text": "👤 Стати учасником"}],
            [{"text": "💬 Менеджер"}],
            [{"text": "❓ Питання адміну"}],
        ],
        "resize_keyboard": True,
    }


def phone_keyboard() -> dict:
    return {
        "keyboard": [[{"text": "Надіслати номер", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def remove_keyboard() -> dict:
    return {"remove_keyboard": True}
