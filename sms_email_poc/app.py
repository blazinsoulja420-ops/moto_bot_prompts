from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response
from sms_email_poc.handlers import process_message
import os
import re
import requests
import time
import logging
from sms_email_poc.commands import run_command
from sms_email_poc.integrations import vin_lookup, oem_discovery
from sms_email_poc import consent
from fastapi import UploadFile, File
from sms_email_poc.integrations import pdf_parser
from sms_email_poc.integrations import suno_client

# outbound SMS helper (uses env vars)
from sms_email_poc.twilio_client import send_sms_message
from pydantic import BaseModel

# Optional Twilio validator (installed via `twilio` package)
try:
    from twilio.request_validator import RequestValidator
except Exception:
    RequestValidator = None

load_dotenv()

app = FastAPI()

@app.post("/sms")
async def sms_webhook(request: Request):
    """Twilio will POST form-encoded fields including `From` and `Body`.

    This endpoint optionally validates the `X-Twilio-Signature` header when
    `TWILIO_AUTH_TOKEN` is present in the environment. If validation fails,
    a 403 is returned.
    """
    # Read form data
    form = await request.form()
    params = dict(form)
    From = params.get("From", "")
    Body = params.get("Body", "")

    # Validate Twilio signature if token and validator are available
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    signature = request.headers.get("X-Twilio-Signature", "")
    if auth_token and RequestValidator is not None:
        validator = RequestValidator(auth_token)
        url = str(request.url)
        valid = validator.validate(url, params, signature)
        if not valid:
            return PlainTextResponse("Invalid Twilio signature", status_code=403)

    reply = await process_message(client="sms", sender=From, text=Body)
    # TwiML simple response
    twiml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Message>{reply}</Message></Response>"
    return Response(content=twiml, media_type="application/xml")

@app.post("/email")
async def email_webhook(request: Request):
    """Receive inbound parsed email payloads (SendGrid Inbound Parse or similar).
    Accepts JSON with `from`, `subject`, and `text` when available.
    """
    data = await request.json()
    sender = data.get("from") or data.get("envelope", {}).get("from")
    text = data.get("text") or data.get("content") or data.get("plain") or ""
    reply = await process_message(client="email", sender=sender, text=text)

    # Optionally forward the reply as an SMS. Detection methods (in order):
    # - explicit `sms_to` JSON field
    # - a line in the email body like `SMS-TO: +1555...`
    # - environment variable `DEFAULT_SMS_FORWARD` (useful for testing)
    sms_to = None
    if isinstance(data, dict) and data.get("sms_to"):
        sms_to = data.get("sms_to")
    else:
        m = re.search(r"sms[-_ ]?to:\s*(\+?[0-9\-\s]+)", text, re.IGNORECASE)
        if m:
            sms_to = m.group(1).strip()
    if not sms_to:
        sms_to = os.getenv("DEFAULT_SMS_FORWARD")

    sms_result = None
    if sms_to:
        try:
            sms_result = send_sms_message(sms_to, reply)
        except Exception as e:
            sms_result = {"error": str(e)}

    # Return both the preview and any SMS forwarding result.
    out = {"status": "ok", "reply_preview": reply}
    if sms_to:
        out["sms_forward"] = {"to": sms_to, "result": sms_result}

    return out

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    """Receive Telegram webhook updates and reply via the Bot API.

    Configure your Telegram bot's webhook to point to `/telegram` on your
    public URL. The bot token must be set in `TELEGRAM_BOT_TOKEN` in `.env`.
    """
    # Optional secret token verification (set TELEGRAM_WEBHOOK_SECRET in .env)
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header != secret:
            return PlainTextResponse("Invalid telegram secret", status_code=403)

    data = await request.json()
    # Telegram may send different update types; prefer `message` then `edited_message`.
    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return {"ok": True}

    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text", "")

    reply = await process_message(client="telegram", sender=str(chat_id), text=text)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token and chat_id is not None:
        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": reply}
        try:
            requests.post(send_url, json=payload, timeout=5)
        except Exception as e:
            logging.exception("Failed to send Telegram reply: %s", e)

    return {"ok": True}


class RunRequest(BaseModel):
    name: str
    args: dict | None = None


@app.post("/run")
async def run_endpoint(req: RunRequest, request: Request):
    """Execute a whitelisted command. Requires `X-ADMIN-TOKEN` header.

    This endpoint intentionally restricts executable commands to a whitelist
    defined in `commands.py` and is protected by `ADMIN_TOKEN`.
    """
    admin_token = os.getenv("ADMIN_TOKEN")
    header = request.headers.get("X-ADMIN-TOKEN")
    if admin_token and header != admin_token:
        return PlainTextResponse("Unauthorized", status_code=401)

    result = run_command(req.name, req.args)
    return result


class SMSRequest(BaseModel):
    to: str
    body: str


@app.post("/send_sms")
async def send_sms_endpoint(req: SMSRequest, request: Request):
    """Send an outbound SMS via Twilio.

    This endpoint requires an admin token in the `X-ADMIN-TOKEN` header to
    prevent open relays. Set `ADMIN_TOKEN` in your `.env` and include the same
    value as the header when calling the endpoint.
    """
    admin_token = os.getenv("ADMIN_TOKEN")
    header = request.headers.get("X-ADMIN-TOKEN")
    if admin_token and header != admin_token:
        return PlainTextResponse("Unauthorized", status_code=401)

    try:
        result = send_sms_message(req.to, req.body)
        return {"status": "sent", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class AudioRequest(BaseModel):
    prompt: str
    voice: str | None = None
    model: str | None = None


@app.post('/generate_audio')
async def generate_audio_endpoint(req: AudioRequest, request: Request):
    """Generate audio via Suno.ai. Protected by `X-ADMIN-TOKEN` header when ADMIN_TOKEN set."""
    admin_token = os.getenv("ADMIN_TOKEN")
    header = request.headers.get("X-ADMIN-TOKEN")
    if admin_token and header != admin_token:
        return PlainTextResponse("Unauthorized", status_code=401)

    if not req.prompt:
        return {"ok": False, "error": "empty_prompt"}

    res = suno_client.generate_audio(req.prompt, voice=req.voice, model=req.model)
    return res


class VinRequest(BaseModel):
    vin: str


@app.post("/vin_lookup")
async def vin_lookup_endpoint(req: VinRequest):
    """Decode a VIN using NHTSA and return basic vehicle info."""
    vin = (req.vin or '').strip()
    if not vin:
        return {"ok": False, "error": "empty_vin"}
    res = vin_lookup.decode_vin(vin)
    if not res:
        return {"ok": False, "error": "decode_failed"}
    return {"ok": True, "vehicle": res}


class DiscoverRequest(BaseModel):
    make: str | None = None
    model: str | None = None
    year: str | None = None
    vin: str | None = None


@app.post('/discover_manuals')
async def discover_manuals(req: DiscoverRequest):
    """Return candidate manual URLs for a vehicle. If `vin` provided, use it to fill make/model/year."""
    make = req.make
    model = req.model
    year = req.year
    if req.vin and (not make or not model):
        decoded = vin_lookup.decode_vin(req.vin)
        if decoded:
            make = make or decoded.get('Make')
            model = model or decoded.get('Model')
            year = year or decoded.get('ModelYear')

    if not make:
        return {"ok": False, "error": "need_make_or_vin"}

    candidates = oem_discovery.candidate_manuals(make or '', model or '', year or '')
    return {"ok": True, "candidates": candidates}


class FetchRequest(BaseModel):
    url: str
    allow_download: bool = False


@app.post('/discover_manuals/fetch')
async def fetch_manual(req: FetchRequest):
    """Inspect a manual URL and optionally download PDF bytes (only if allow_download=True)."""
    if not req.url:
        return {"ok": False, "error": "empty_url"}
    res = oem_discovery.fetch_manual(req.url, allow_download=req.allow_download)
    return res


class ManualDownloadRequest(BaseModel):
    url: str


@app.post('/discover_manuals/request_download')
async def request_manual_download(req: ManualDownloadRequest):
    """Create a short-lived consent token for downloading a manual.

    Returns a token which must be confirmed via `/discover_manuals/confirm_download`.
    """
    if not req.url:
        return {"ok": False, "error": "empty_url"}
    token = consent.create_consent({'url': req.url}, ttl=600)
    return {"ok": True, "token": token, "note": "Confirm with /discover_manuals/confirm_download"}


class ManualDownloadConfirm(BaseModel):
    token: str


@app.post('/discover_manuals/confirm_download')
async def confirm_manual_download(req: ManualDownloadConfirm):
    """Confirm a manual download token and attempt to fetch the PDF."""
    rec = consent.verify_consent(req.token)
    if not rec:
        return {"ok": False, "error": "invalid_or_expired_token"}
    url = rec.get('url')
    if not url:
        return {"ok": False, "error": "no_url_in_token"}
    res = oem_discovery.fetch_manual(url, allow_download=True)
    # If PDF bytes were returned, write to data/manuals folder for parsing
    if res.get('ok') and res.get('content'):
        base = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(base, exist_ok=True)
        fname = os.path.join(base, f"manual_{int(time.time())}.pdf")
        with open(fname, 'wb') as f:
            f.write(res['content'])
        res['saved_path'] = fname
    return res


@app.post('/upload_manual')
async def upload_manual(file: UploadFile = File(...)):
    """Upload a PDF manual and parse it for PID/DTC tables.

    Saves uploaded file under `sms_email_poc/data/manuals/` and attempts to
    extract PID/DTC entries into `data/pid_db.json`.
    """
    if not file.filename.lower().endswith('.pdf'):
        return {'ok': False, 'error': 'only_pdf_allowed'}
    base = os.path.join(os.path.dirname(__file__), 'data', 'manuals')
    os.makedirs(base, exist_ok=True)
    target = os.path.join(base, file.filename)
    with open(target, 'wb') as f:
        content = await file.read()
        f.write(content)

    parsed = pdf_parser.parse_pdf_for_pids(target)
    if parsed.get('ok') and parsed.get('entries'):
        saved = pdf_parser.save_pid_db(parsed['entries'])
        return {'ok': True, 'saved_pid_db': saved, 'parsed': parsed}
    return parsed
