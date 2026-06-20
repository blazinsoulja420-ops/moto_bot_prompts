"""Master Mechanic automation: formats diagnostic reports per user's template.

This module provides a simulated diagnostic report generator using the
enhanced output template. It accepts a short description or DTC list and
returns a markdown-formatted report ready to send back to the user.
"""
from typing import List, Dict, Optional

import json
import pkgutil
import os


# Load DTC DB from data file if available, otherwise fall back to small built-in map
def _load_dtc_db() -> Dict[str, Dict[str, str]]:
    try:
        base = os.path.dirname(__file__)
        data_path = os.path.join(base, 'data', 'dtc_db.json')
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    # fallback
    return {
        "P0300": {"desc": "Random/Multiple Cylinder Misfire", "oem": "Kia: 12-001-19"},
        "P0171": {"desc": "System Too Lean (Bank 1)", "oem": "Honda: P0171-1"},
        "P0420": {"desc": "Catalyst System Efficiency Below Threshold (Bank 1)", "oem": "Cadillac: 8-042-20"},
    }


_DTC_DB = _load_dtc_db()


def _parse_input(text: str) -> Dict[str, object]:
    """Very small parser: extract DTCs (like P0300) and free text notes."""
    tokens = text.upper().split()
    dtcs: List[str] = []
    notes = []
    for t in tokens:
        if len(t) >= 4 and (t[0] == 'P' or t[0] == 'C' or t[0] == 'U') and t[1:].isdigit():
            dtcs.append(t[:5])
        else:
            notes.append(t)
    return {"dtcs": dtcs, "notes": " ".join(notes)}


def _format_dtc_block(code: str) -> str:
    info = _DTC_DB.get(code, {})
    desc = info.get("desc", "Description unavailable (generic SAE)")
    oem = info.get("oem", "OEM ref unavailable")
    # Simple probability-weighted causes (simulated)
    causes = [
        (70, "Ignition system (plugs/coils)"),
        (40, "Fuel system - injector or pump"),
        (25, "Vacuum leak or intake leak"),
        (10, "Cam/crank sensor or timing")
    ]
    causes_text = "  ".join([f"{p}% ━━ {c}" for p, c in causes])
    block = (
        "┌──────────────────────────────────────────────┐\n"
        f"│ Code: {code} │\n"
        f"│ Status: [Active] │\n"
        f"│ Description: {desc} │\n"
        f"│ OEM Ref: {oem} │\n"
        "└──────────────────────────────────────────────┘\n"
        f"Common Causes (Probability-Weighted):  {causes_text}\n"
    )
    return block


def generate_report(input_text: str, ocr_text: str | None = None, obd_data: dict | None = None) -> str:
    """Generate a markdown report using the enhanced template.

    Parameters:
    - input_text: free-text or DTC list supplied by the caller
    - ocr_text: (optional) screen-extracted text from the X431 or scanner
    - obd_data: (optional) structured OBD-II data dict from the scan tool

    This generator is simulated — for real-world integration pass parsed
    screen values and OBD-II outputs.
    """
    # Combine inputs for parsing
    combined = input_text or ""
    if ocr_text:
        combined += "\n" + ocr_text
    if obd_data:
        try:
            combined += "\n" + " ".join([str(v) for v in obd_data.values()])
        except Exception:
            combined += "\n" + str(obd_data)

    parsed = _parse_input(combined)
    dtcs: List[str] = parsed["dtcs"]
    notes: str = parsed["notes"]

    # Issue summary
    issue_summary = "Detected diagnostic request. Generating Master Mechanic report."
    if dtcs:
        issue_summary = f"Detected DTCs: {', '.join(dtcs)} — starting focused analysis."

    # X431 menu path (generic)
    menu_path = (
        "1. Tap: Intelligent Diagnose\n"
        "2. Select: VIN entry (Auto VIN or manual)\n"
        "3. Navigate to: Diagnosis → Engine / Powertrain → Read DTCs\n"
        "4. Execute: Read DTCs / Data Stream"
    )

    # DTC details section
    dtc_details = ""
    if dtcs:
        for d in dtcs:
            dtc_details += _format_dtc_block(d) + "\n"
    else:
        dtc_details = (
            "┌──────────────────────────────────────────────┐\n"
            "│ Code: [none] │\n"
            "│ Status: [n/a] │\n"
            "│ Description: No DTCs provided │\n"
            "└──────────────────────────────────────────────┘\n"
            "Common Causes (Probability-Weighted):  50% ━━ Sensor/communication  30% ━━ Intermittent fault  20% ━━ Mechanical\n"
        )

    # Recommended tests (simulated branching)
    tests = (
        "□ Test 1: Visual inspection & clear codes — ignition OFF -> wait 10s -> ignition ON -> Read DTCs\n"
        "   - Expected: No new permanent codes\n"
        "   - If fails: perform freeze frame check and capture live PIDs\n"
        "□ Test 2: Data stream monitoring — engine running\n"
        "   - Monitor PID: Short-Term Fuel Trim (STFT), Long-Term Fuel Trim (LTFT), RPM, MAP\n"
        "   - Normal ranges: STFT ±10%, LTFT ±10%\n"
    )

    # Special function placeholder
    special = (
        "Function Name: [If adaptive learning needed — Throttle Adaptation]\n"
        "X431 Location: Special Functions → ECM → Throttle Adaptation\n"
        "Required Addon: None\nTime Required: 5-10 minutes\nBattery Min: 12.0V\n"
    )

    precautions = (
        "SAFETY: - Wear eye protection; secure vehicle; set parking brake\n"
        "BATTERY: - Recommended: battery charger if below 12.0V\n"
        "IGNITION STATES: - Follow prompts exactly; do not disconnect during adapt procedures\n"
    )

    estimate = (
        "Time to Diagnose: 15-45 minutes\n"
        "Time to Repair: 0.5-2 hours (depends on parts)\n"
        "Parts Cost: $50-200 estimated\n"
    )

    # Gemini screen section — simulated guidance
    gemini = (
        f"What Gemini Sees On Screen: {notes or '[no screen text provided]'}\n"
        "My Analysis of Screen Data: Check highlighted DTCs and prioritize ignition and fuel systems.\n"
        "Next Step (Based on Current Screen): Tap 'Read DTCs' then 'Data Stream' — watch STFT/LTFT while revving to 2500 RPM.\n"
        "Screen Change Verification: Expect DTC list or 'Success ✓' message; if 'VCI disconnected' appears, verify DBScar VII connection.\n"
    )

    # If OBD structured data provided, append a short summary
    if obd_data:
        gemini += "\nOBD-II Summary:\n"
        try:
            for k, v in (obd_data.items() if isinstance(obd_data, dict) else []):
                gemini += f"- {k}: {v}\n"
        except Exception:
            gemini += f"- {str(obd_data)}\n"

    # Compose final markdown following user's template headings
    md = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ISSUE SUMMARY━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{issue_summary}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ X431 MENU PATH━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{menu_path}\n"
        "Full Path: `Intelligent Diagnose → [VIN entry] → Diagnosis → [System] → [Function]`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ DTC DETAILS━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{dtc_details}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ RECOMMENDED TESTS━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{tests}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ SPECIAL FUNCTION (if applicable)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{special}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ PRECAUTIONS━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{precautions}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ESTIMATED REPAIR INFO━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{estimate}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ GEMINI SCREEN SHARE ANALYSIS (Live Data)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{gemini}\n"
    )

    return md
