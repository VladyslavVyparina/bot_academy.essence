HEAD
# Academy Essence — Telegram Community Bot

A FastAPI-based Telegram bot and admin panel for community event registration, payments, support chats, and CRM sync.

## Features

- Telegram bot (long polling or webhook)
- Onboarding (full name, phone)
- Roles: `lead` / `guest` / `member`
- Event registration with seats, waitlist, RSVP
- WayForPay payments (events + membership)
- Discount pricing per role (guest / lead / member)
- Reminder pipeline (unpaid, RSVP, 24h, 3h)
- Web admin panel (`/admin`) with signed access link from Telegram
- Live chats, support inbox, broadcasts, push messages
- Excel import/export
- SendPulse CRM contact sync

## Stack

- Python 3 + FastAPI + Uvicorn
- SQLite
- Jinja2 admin templates
- Telegram Bot API
- WayForPay API
- SendPulse API

## Quick start

1. Copy env file and fill values:

```bash
cp .env.example .env
```

2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run the app:

```bash
./run.sh
# or
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open: `http://localhost:8000/admin`

## Environment variables

See `.env.example`. Required / important keys:

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Secret for webhook mode |
| `ADMIN_TELEGRAM_IDS` | Comma-separated Telegram user IDs with admin access |
| `ADMIN_SUPPORT_NOTIFY_CHAT_ID` | Group/topic for support notifications |
| `APP_SECRET_KEY` | Signing key for admin tokens |
| `APP_BASE_URL` | Public base URL used in payment/media links |
| `ADMIN_PUBLIC_URL` | Optional public URL for admin links (VPS IP/domain) |
| `USE_POLLING` | `true` for VPS without HTTPS domain |
| `WAYFORPAY_MERCHANT_LOGIN` | WayForPay merchant login |
| `WAYFORPAY_SECRET_KEY` | WayForPay secret key |
| `WAYFORPAY_RETURN_URL` | Browser return URL after payment |
| `WAYFORPAY_SERVICE_URL` | Payment callback URL (`/wayforpay/callback`) |
| `SENDPULSE_API_KEY` | SendPulse API key (or OAuth pair below) |
| `SENDPULSE_CLIENT_ID` / `SENDPULSE_CLIENT_SECRET` | Optional OAuth credentials |
| `SENDPULSE_ADDRESSBOOK_ID` | Optional address book ID |

Never commit real secrets. Keep production values only on the server.

## Telegram modes

### Polling (no domain)

```env
USE_POLLING=true
APP_BASE_URL=http://YOUR_VPS_IP:8000
ADMIN_PUBLIC_URL=http://YOUR_VPS_IP:8000
```

No webhook setup required.

### Webhook (HTTPS domain)

```env
USE_POLLING=false
```

Set webhook:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://your-domain.com/telegram/webhook","secret_token":"<TELEGRAM_WEBHOOK_SECRET>"}'
```

## Payments (WayForPay)

Flow:

1. Admin creates an event with base prices and optional discount prices.
2. User opens the event in the bot and registers.
3. Bot shows a pay button with a WayForPay invoice/custom payment URL.
4. Payment confirmation arrives via callback and/or status polling.
5. On successful event payment, `lead` becomes `guest` (members stay members).

Per-event payment URLs can be set for:

- guest
- lead
- member

Membership payment URL can be assigned when approving applications.

Callback endpoint: `POST /wayforpay/callback`

## SendPulse CRM

Contacts are synced on:

- onboarding completion
- successful payment
- membership approval
- feedback submission

If sync fails, check logs prefixed with `[SendPulse]`.

## Bot commands

- `/start` — start / resume onboarding (supports event deep-links)
- `/events` — upcoming events
- `/register_event <id>` — register for an event
- `/admin` — one-time signed admin panel link (admin IDs only)

## Admin panel

Access via `/admin` command in Telegram (for IDs listed in `ADMIN_TELEGRAM_IDS`).

Main sections:

- Dashboard / events
- Funnel
- Applications
- Broadcast / Push / Reminders
- Live chats / Support
- Tags / Membership / Bot menu
- Excel import

## Project structure

```text
app/
  main.py              # FastAPI app, bot handlers, admin routes
  config.py            # env settings
  database.py          # SQLite schema + migrations
  services/
    telegram_api.py    # Telegram helpers
    wayforpay.py       # invoices + callbacks
    sendpulse.py       # CRM sync
    reminders.py       # reminder scheduling
templates/             # admin UI
uploads/               # media uploads
.env.example           # env template
run.sh                 # start script
```

## Restart on VPS

```bash
cd /root/bot_academy.essence && pkill -f "run.sh|uvicorn app.main:app|python3 -m app.main|python3 app/main.py" ; nohup ./run.sh >> bot.log 2>&1 & disown
```

Check process:

```bash
pgrep -af "uvicorn app.main:app"
```

## Security notes

- Do not store production tokens in the repository.
- Rotate Telegram / WayForPay / SendPulse credentials if they were ever shared.
- For production: HTTPS, restricted admin IDs, backups, and log monitoring.
=======
# bot_academy.essence
>>>>>>> aa1f8739a60d2e097cfe9c015cce1490e9faceef
