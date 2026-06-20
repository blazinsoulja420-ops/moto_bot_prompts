import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")


def send_sms_message(to: str, body: str) -> dict:
    """Send an SMS using Twilio REST API.

    Returns a small dict with `sid` and `status` on success. Raises RuntimeError
    if configuration is missing or Twilio client raises an exception.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        raise RuntimeError("Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")

    try:
        from twilio.rest import Client
    except Exception as e:
        raise RuntimeError("twilio package required: pip install twilio") from e

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(body=body, from_=TWILIO_PHONE_NUMBER, to=to)
    return {"sid": getattr(message, "sid", None), "status": getattr(message, "status", None)}
