"""Safe, whitelisted command implementations.

Expose `run_command(name, args)` to execute only pre-approved tasks.
"""
from typing import Any, Dict

from sms_email_poc.integrations import teamviewer
from sms_email_poc.integrations import screen_capture
from sms_email_poc.integrations import gemini_client
from sms_email_poc import master_mechanic


def _backup_db(args: Dict[str, Any]) -> str:
    # Placeholder: implement real backup logic here.
    return "backup_db: simulated backup completed"


def _status_report(args: Dict[str, Any]) -> str:
    return "status: all systems nominal"


# Remote diagnose orchestration (protected via /run endpoint only)
def _remote_diagnose(args: Dict[str, Any]) -> str:
    # args may include 'obd_data' (dict) or 'notes'
    ok, msg = teamviewer.open_teamviewer()
    parts = [f"teamviewer: {msg}"]

    img = None
    ocr_text = None
    try:
        img = screen_capture.capture_screen()
        if img:
            parts.append(f"screenshot: saved to {img}")
            ocr_text = screen_capture.ocr_image(img)
            if ocr_text:
                parts.append("ocr: text extracted")
            else:
                parts.append("ocr: unavailable or returned no text")
        else:
            parts.append("screenshot: not available (mss not installed or headless)")
    except Exception as e:
        parts.append(f"screenshot error: {e}")

    # Combine any provided OBD data with OCR text and Gemini analysis for the report
    obd = args.get('obd_data') if args else None
    combined_input = ''
    if obd:
        # simple join if dict
        try:
            combined_input += ' '.join([str(v) for v in (obd.values() if isinstance(obd, dict) else [obd])])
        except Exception:
            combined_input += str(obd)
    if ocr_text:
        combined_input += '\n' + ocr_text
    # If Gemini configured, call it to get multimodal analysis
    gemini_out = None
    if img:
        try:
            gemini_out = gemini_client.analyze_image(img, prompt='Extract DTCs, PIDs and likely causes in JSON or plain text.')
            if gemini_out:
                # Prefer structured 'text' or JSON content
                if isinstance(gemini_out, dict):
                    gem_text = gemini_out.get('text') or gemini_out.get('response') or str(gemini_out)
                else:
                    gem_text = str(gemini_out)
                combined_input += '\n' + gem_text
        except Exception:
            pass
    if not combined_input:
        combined_input = args.get('notes', 'No additional data provided') if args else 'No additional data provided'

    report = master_mechanic.generate_report(combined_input, ocr_text=ocr_text, obd_data=obd)

    # Very small confidence heuristic
    confidence = 0.4
    if 'P0' in combined_input.upper() or 'P0' in (ocr_text or '').upper():
        confidence = 0.78
    if obd and isinstance(obd, dict) and any(k.lower().startswith('p') for k in obd.keys()):
        confidence = 0.9

    parts.append(f'report_generated: confidence={confidence:.2f}')
    return '\n'.join(parts) + '\n\n' + report

# Whitelist mapping
_COMMANDS = {
    "backup_db": _backup_db,
    "status_report": _status_report,
    "remote_diagnose": _remote_diagnose,
}


def run_command(name: str, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    args = args or {}
    if name not in _COMMANDS:
        return {"ok": False, "error": "unknown_command", "message": f"{name} is not allowed"}
    try:
        res = _COMMANDS[name](args)
        return {"ok": True, "result": res}
    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}
