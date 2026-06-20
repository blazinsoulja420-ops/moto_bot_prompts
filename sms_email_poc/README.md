PoC SMS + Email Assistant

Overview
- Minimal FastAPI proof-of-concept that accepts incoming SMS (Twilio) and inbound email (SendGrid-style) webhooks.
- Parses simple commands and returns a canned reply. Safe by default — it will not run arbitrary shell commands.

Setup
1. Create and activate a Python venv, then install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and add credentials.

Run locally

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Expose to the internet for webhooks
- Use `ngrok http 8000` and set Twilio's Messaging webhook to `https://<ngrok>/sms`
- For SendGrid Inbound Parse, point the webhook to `https://<ngrok>/email`

Twilio request validation
- If you set `TWILIO_AUTH_TOKEN` in `.env` the app will validate incoming SMS
	requests using Twilio's `X-Twilio-Signature` header. This prevents spoofed
	requests. Make sure the public webhook URL you give Twilio (ngrok URL or
	deployed URL) matches the URL used when Twilio signs the request.

Configuring Twilio webhook
- In the Twilio Console go to the phone number -> Messaging -> A MESSAGE COMES IN
	and paste your public `/sms` URL. Choose HTTP POST.

 Note: The `twilio` package is listed in `requirements.txt`. If it's missing,
 signature validation will be skipped but the endpoint will still process messages.

Outbound SMS via Twilio
------------------------
- Configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` in `.env`.
- The app exposes a protected test endpoint `/send_sms` you can use to send SMS
	programmatically. It expects JSON `{ "to": "+1...", "body": "message" }`
	and requires the `X-ADMIN-TOKEN` header to match `ADMIN_TOKEN` from `.env`.

Example `curl` (replace values):

```bash
curl -X POST https://<your-host>/send_sms \
	-H "Content-Type: application/json" \
	-H "X-ADMIN-TOKEN: your_admin_token" \
	-d '{"to":"+15551234567","body":"Hello from your PoC"}'
```

Security note: `ADMIN_TOKEN` is a convenience for local testing. For production,
use stronger authentication (OAuth, signed webhooks, IP allowlists) and avoid
exposing any unauthenticated outbound message endpoint.
Notes & Next steps
- Add provider-specific request validation (Twilio signature, SendGrid verification).
- Implement a secure authentication/whitelist for `run:` commands before executing anything.
- Add handlers for calendar, reminders, and third-party APIs.
- I can wire credentials and add a simple `run` whitelist if you want — say which scripts or services to enable first.

Telegram bot support
--------------------
- Create a bot with BotFather in Telegram and get the `BOT_TOKEN`.
- Set `TELEGRAM_BOT_TOKEN` in your `.env`.
- If running locally with ngrok, set the bot webhook (replace URL):

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
	-d "url=https://<ngrok-id>.ngrok-free.dev/telegram"
```

- When Telegram sends updates to `/telegram`, the app will parse incoming messages,
	forward them to the same `process_message` handler, and reply via the Bot API.

Example quick test: send your bot a message in Telegram and watch the server logs
or call the webhook test above.

Telegram webhook security
-------------------------
You can set a `TELEGRAM_WEBHOOK_SECRET` in your `.env`. If set, the app will
require incoming webhook requests to include the header
`X-Telegram-Bot-Api-Secret-Token` with that exact value. When setting the
webhook, include the same secret with `setWebhook` using the `secret_token`
parameter.

Run whitelisted commands securely
--------------------------------
The app exposes a protected `/run` endpoint which executes only pre-approved
commands defined in `sms_email_poc/commands.py`.
To execute a command, call `/run` with JSON `{"name":"backup_db","args":{}}`
and include the `X-ADMIN-TOKEN` header matching `ADMIN_TOKEN` from your `.env`.

Example curl (run a whitelist command):

```bash
curl -X POST https://<your-host>/run \
	-H "Content-Type: application/json" \
	-H "X-ADMIN-TOKEN: <ADMIN_TOKEN>" \
	-d '{"name":"status_report"}'
```

Security notes:
- Do not enable execution of arbitrary `run:` commands from inbound messages.
- Keep `ADMIN_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` secret and rotate if leaked.
