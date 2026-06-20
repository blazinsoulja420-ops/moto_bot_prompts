import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("assistant")

from sms_email_poc import consent
from sms_email_poc.integrations import x431_parser
from sms_email_poc import commands
from sms_email_poc.integrations import vin_lookup, oem_discovery
from sms_email_poc.integrations import suno_client
import json
import os
import re
import random


# Simple consent instruction template
_CONSENT_PROMPT = (
    "Remote diagnose requested. Reply with 'confirm <token>' to allow remote session. "
    "This token expires in 5 minutes. Example: confirm abc12345"
)


async def process_message(client: str, sender: str, text: str) -> str:
    """Parse incoming text and return a reply string.
    This is a minimal PoC parser; expand with safe command handlers.
    """
    logger.info("Incoming message from %s via %s: %s", sender, client, text)
    if not text:
        return "Sorry, I couldn't read your message. Send 'help' for commands."

    body = text.strip()
    low = body.lower()

    if low in ("help", "?"):
        return (
            "Available commands: help, status, next-meeting, vin:<vin>, manuals:<make> [model] [year], run:<script>\n"
            "Examples: vin: 1HGCM82633A004352, manuals: Toyota Camry 2012"
        )

    # VIN lookup: `vin: <vin>` or `vin <vin>`
    if low.startswith('vin:') or low.startswith('vin '):
        rest = body.split(':', 1)[1].strip() if ':' in body else body.split(' ', 1)[1].strip()
        if not rest:
            return "Please provide a VIN, e.g. 'vin: 1HGCM82633A004352'"
        try:
            decoded = vin_lookup.decode_vin(rest)
            if not decoded:
                return "VIN decode failed or returned no data."
            # Format a short summary
            make = decoded.get('Make') or decoded.get('Manufacturer') or 'Unknown'
            model = decoded.get('Model') or 'Unknown'
            year = decoded.get('ModelYear') or decoded.get('Year') or 'Unknown'
            return f"VIN decoded: {make} {model} ({year})\nFull: {decoded}"
        except Exception:
            return "Error decoding VIN."

    # Manual discovery: `manuals: <make> [model] [year]` or `manuals <make> ...`
    if low.startswith('manuals:') or low.startswith('manuals '):
        rest = body.split(':', 1)[1].strip() if ':' in body else body.split(' ', 1)[1].strip()
        parts = rest.split()
        if not parts:
            return "Please provide at least a make, e.g. 'manuals: Toyota Camry 2012'"
        make = parts[0]
        model = parts[1] if len(parts) > 1 else ''
        year = parts[2] if len(parts) > 2 else ''
        try:
            candidates = oem_discovery.candidate_manuals(make, model, year)
            if not candidates:
                return "No manual candidates found."
            # Return top 5 candidates
            out = [f"{i+1}. {c.get('title') or c.get('url') or c}" for i, c in enumerate(candidates[:5])]
            return "Candidate manuals:\n" + "\n".join(out)
        except Exception:
            return "Error searching for manuals."

    # DTC lookup: `dtc: P0300` or `dtc P0300`
    if low.startswith('dtc:') or low.startswith('dtc '):
        code = body.split(':', 1)[1].strip() if ':' in body else body.split(' ', 1)[1].strip()
        if not code:
            return "Please provide a DTC code, e.g. 'dtc: P0300'"
        # Load local DTC DB
        try:
            base = os.path.join(os.path.dirname(__file__), 'data')
            path = os.path.join(base, 'dtc_db.json')
            if not os.path.exists(path):
                return "DTC database not available."
            with open(path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            entry = db.get(code.upper())
            if not entry:
                return f"DTC {code.upper()} not found in local DB."
            return f"{code.upper()}: {entry.get('desc')} (OEM: {entry.get('oem')})"
        except Exception:
            return "Error reading DTC database."

    # PID search: `pid: <term>` or `pid <term>`
    if low.startswith('pid:') or low.startswith('pid '):
        term = body.split(':', 1)[1].strip() if ':' in body else body.split(' ', 1)[1].strip()
        if not term:
            return "Please provide a search term for PIDs, e.g. 'pid: coolant'"
        try:
            base = os.path.join(os.path.dirname(__file__), 'data')
            path = os.path.join(base, 'pid_db.json')
            if not os.path.exists(path):
                return "PID database not available. Upload manuals to build PID DB."
            with open(path, 'r', encoding='utf-8') as f:
                pid_db = json.load(f)
            results = []
            for pid, info in pid_db.items():
                text = ' '.join([str(v) for v in (info.get('name',''), info.get('desc',''))])
                if term.lower() in text.lower() or term.lower() in pid.lower():
                    results.append(f"{pid}: {info.get('name')} - {info.get('desc')}")
            if not results:
                return "No PIDs matched your search term."
            return "PID matches:\n" + "\n".join(results[:10])
        except Exception:
            return "Error searching PID database."

    # Audio generation: `audio: <prompt>` or `audio <prompt>` — uses Suno.ai if configured
    if low.startswith('audio:') or low.startswith('audio '):
        prompt = body.split(':', 1)[1].strip() if ':' in body else body.split(' ', 1)[1].strip()
        if not prompt:
            return "Please provide an audio prompt, e.g. 'audio: read this message'"
        try:
            res = suno_client.generate_audio(prompt)
            if res.get('ok'):
                return f"Audio generated: {res.get('path')}"
            return f"Audio generation failed: {res.get('error') or res.get('detail') or res}" 
        except Exception as e:
            return f"Audio generation error: {e}"

    # Master Mechanic diagnostic command (simulate)
    if low.startswith("diagnose:") or low.startswith("mm:"):
        # rest of text after the command
        rest = body.split(":", 1)[1].strip() if ":" in body else ""
        try:
            from sms_email_poc.master_mechanic import generate_report

            report = generate_report(rest)
            return report
        except Exception:
            return "Failed to generate Master Mechanic report."

    # Request a remote diagnose (consent flow)
    if 'remote diagnose' in low or 'diagnose now' in low or low.startswith('diagnose now'):
        # allow optional pasted X431 output after a marker 'x431:'
        x431_data = None
        if 'x431:' in low:
            _, payload = body.split('x431:', 1)
            x431_data = x431_parser.parse_x431_text(payload)

        token = consent.create_consent({'sender': sender, 'notes': body, 'x431': x431_data})
        return f"{_CONSENT_PROMPT}\nToken: {token}"

    # Confirm consent token
    if low.startswith('confirm '):
        _, tok = body.split(' ', 1)
        tok = tok.strip()
        rec = consent.verify_consent(tok)
        if not rec:
            return "Consent token invalid or expired. Request a new remote diagnose."
        # run the remote diagnose via protected run_command (server-side)
        args = {'notes': rec.get('notes'), 'obd_data': rec.get('x431')}
        res = commands.run_command('remote_diagnose', args)
        if res.get('ok'):
            return f"Remote diagnose started. {res.get('result')[:800]}"
        else:
            return f"Remote diagnose failed to start: {res.get('message')}"

    if low.startswith("status"):
        return "All systems nominal. I can run scripts, check calendars, and more (PoC)."

    if low.startswith("next-meeting") or low.startswith("next meeting"):
        # Placeholder: integrate calendar API here
        return "Your next meeting is Mock Meeting at 3:00 PM — integrate Google Calendar for real data."

    if low.startswith("run:"):
        script = body.split(":", 1)[1].strip() if ":" in body else ""
        if not script:
            return "Specify a script name, e.g. 'run: backup_db'."
        # SECURITY: Do NOT execute commands from inbound messages. Require
        # authenticated API calls to `/run` for executing whitelisted tasks.
        return (
            "Run requests must be made through the protected /run API endpoint. "
            "This prevents arbitrary command execution from incoming messages."
        )

    # Diss track generator: `diss: <genre> <name>` or `diss <genre> <name>`
    # Genres supported: r&b, rnb, country, rock, metal, heavy metal
    if low.startswith('diss:') or low.startswith('diss '):
        payload = body.split(':', 1)[1].strip() if ':' in body else body.split(' ', 1)[1].strip()
        if not payload:
            return "Usage: diss: <genre> <name> — genres: r&b, country, rock, metal"

        parts = payload.split()
        genres_map = {'r&b': 'R&B', 'rnb': 'R&B', 'country': 'Country', 'rock': 'Rock', 'metal': 'Heavy Metal', 'heavy': 'Heavy Metal'}
        genre_key = parts[0].lower()
        if genre_key in genres_map and len(parts) > 1:
            genre = genres_map[genre_key]
            target = ' '.join(parts[1:]).strip()
        else:
            # default: assume first token is part of the target
            genre = 'Rock'
            target = payload

        if not target:
            return "Please provide a target name. Example: diss: rock Phantom"

        # Safety: refuse obvious handles, URLs, or phone numbers
        if re.search(r'@|http[s]?://|www\.|\d', target):
            return "Please provide a fictional or consenting target name (no @mentions, URLs, or numbers). Use 'self' for self-roast."

        # Allow 'self' to indicate self-roast
        if target.lower() == 'self':
            target = 'you'

        # Lightweight, non-abusive lyric templates per genre
        def make_rnb(name):
            lines = [
                f"Velvet venom, I whisper and the room bends in my favor,",
                f"{name}, your shadow stumbles while I rise, a braver savior.",
                "Late-night rhythm, sultry strike, my truth will cut like fire,",
                "You made your gamble, now I own the stakes and raise the wire.",
                "Chorus: Slow burn, satin turn, \nI take the spotlight and never fold."
            ]
            return '\n'.join(lines)

        def make_country(name):
            lines = [
                f"I saw you stumble past the silo, {name}, your bluff couldn't stand the gale,",
                "Rust on your promises, dust on your name, you folded under the trail.",
                "Slide guitar lashes, truth bites like a thorn, I plant my flag where you were torn.",
                "Chorus: Bourbon edge and midnight scars, \nI sing you down beneath the stars."
            ]
            return '\n'.join(lines)

        def make_rock(name):
            lines = [
                f"Crank the amps, {name}, watch the skyline split in two,",
                "Lightning riffs, iron fists, there's no comeback for you.",
                "Strings that shred the stories you thought you'd leave behind.",
                "Chorus: Blood and neon, stage like stone, \nI roar so loud your memory unwinds."
            ]
            return '\n'.join(lines)

        def make_metal(name):
            lines = [
                f"Ravage the night for {name}, the heavens crack with sound,",
                "Iron lungs, a fevered stomp, I bury your last round.",
                "Molten screams and serrated chords, I carve the final line.",
                "Chorus: Thrash and thunder, crown of coal, \nYou burn away while my war drums climb."
            ]
            return '\n'.join(lines)

        # Pick generator
        g = genre.lower()
        if 'r&b' in g or 'rnb' in g:
            lyrics = make_rnb(target)
        elif 'country' in g:
            lyrics = make_country(target)
        elif 'metal' in g or 'heavy' in g:
            lyrics = make_metal(target)
        else:
            lyrics = make_rock(target)

        # Optionally shorten if very long
        return f"Genre: {genre}\nTarget: {target}\n\n" + lyrics

    return "Command not recognized. Send 'help' for available commands."