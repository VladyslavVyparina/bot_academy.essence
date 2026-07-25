# Telegram Community Bot (MVP)

MVP-реалізація під ваше ТЗ:
- Telegram-бот (через webhook)
- Онбординг (ПІБ, email, contact)
- Сегментація `guest/member`
- Реєстрація на події
- Каркас оплати через WayForPay + callback
- Нагадування по етапах
- Адмін-панель у web (`/admin`) з лінком через команду `/admin` у Telegram
- Каркас інтеграції у SendPulse CRM

## 1) Швидкий старт

1. Скопіюйте `.env.example` в `.env` і заповніть значення.
2. Встановіть залежності: `pip install -r requirements.txt`
3. Запустіть: `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

**VPS без домену:** у `.env` вкажіть `USE_POLLING=true` та `ADMIN_PUBLIC_URL=http://ВАША_VPS_IP:8000`, щоб кнопка «Відкрити адмін-панель» працювала.

## 2) Telegram: polling (без домену) або webhook

**Без домену** — використовується long polling. У `.env` вкажіть:
- `USE_POLLING=true`
- `APP_BASE_URL=http://ВАШ_VPS_IP:8000` (для посилання /admin)

Webhook налаштовувати не потрібно.

**З доменом і HTTPS** — встановіть `USE_POLLING=false` і налаштуйте webhook:
```
POST https://api.telegram.org/bot<TOKEN>/setWebhook
Body: {"url":"https://your-domain.com/telegram/webhook","secret_token":"..."}
```

## 3) WayForPay

**Потік оплати за події:**
1. Адмін створює подію в панелі з ціною (гость / учасник)
2. Подія з'являється в боті у юзерів
3. Юзер натискає «Зареєструватися» → кнопка «💳 Оплатити» з посиланням на WayForPay
4. Ціна береться з події (guest_price_uah або member_price_uah)

В `.env` потрібно задати:
- `WAYFORPAY_MERCHANT_LOGIN`
- `WAYFORPAY_SECRET_KEY`
- `WAYFORPAY_RETURN_URL` — куди повертати після оплати
- `WAYFORPAY_SERVICE_URL` — callback для підтвердження (напр. `https://your-domain.com/wayforpay/callback`)

Callback endpoint: `/wayforpay/callback`. Для роботи WayForPay потрібен публічний HTTPS-домен.

## 4) SendPulse CRM (інтегровано)

Контакти автоматично синхронізуються в SendPulse Addressbook «Community Bot Contacts»:
- при завершенні онбордингу
- при оплаті
- при надсиланні фідбеку
- при підтвердженні учасника

**Налаштування в `.env` (один із варіантів):**

1. **API Key** — `SENDPULSE_API_KEY` з SendPulse (Settings → API → API keys). Використовується як Bearer token.

2. **OAuth** — якщо API key не працює:
   - `SENDPULSE_CLIENT_ID`
   - `SENDPULSE_CLIENT_SECRET`

3. **Адресна книга** — `SENDPULSE_ADDRESSBOOK_ID` (опційно). Якщо не вказано, створюється книга «Community Bot Contacts».

**Якщо дані не передаються:**
- Перевірте, що ключ/токен дійсний у SendPulse.
- Перегляньте логи — помилки API виводяться з префіксом `[SendPulse]`.
- Спробуйте OAuth замість API key, якщо отримуєте 401.

## 5) Команди бота (MVP)

- `/start` — старт онбордингу.
- `/events` — список майбутніх подій.
- `/register_event <id>` — реєстрація на подію.
- `/admin` — для admin IDs повертає одноразове посилання в адмін-панель.

## 6) Що реалізовано як каркас (для розширення)

- Ролі `guest/member/admin`.
- Етапи нагадувань через таблицю `reminders` + воркер.
- База SQLite: `users`, `events`, `registrations`, `feedback`, `reminders`.
- Адмін-лендінг + dashboard + створення подій.

## 7) Важливо по безпеці

- Не зберігайте продакшн-токени у коді.
- Рекомендується негайно перевипустити токен Telegram, якщо він вже публічно передавався.
- Для продакшну додайте HTTPS, rate limiting, audit logs, шифрування backup.
