import re
import json
import os
from typing import Dict, List
from PyPDF2 import PdfReader


def extract_text_from_pdf(path: str) -> str:
    """Extract text from a PDF using PyPDF2. Returns concatenated page text."""
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or '')
            except Exception:
                texts.append('')
        return '\n'.join(texts)
    except Exception:
        return ''


def extract_pid_entries(text: str) -> List[Dict[str, str]]:
    """Try to find PID-related table rows or lines in extracted text.

    Returns a list of dicts like {code: 'P0300', name: 'Misfire', notes: '...'}
    This is heuristic and will need refinement per-manufacturer.
    """
    entries = []
    # Find DTC codes anywhere
    dtc_re = re.compile(r'\b([PCU][0-9]{4})\b', re.IGNORECASE)
    dtcs = sorted({m.group(1).upper() for m in dtc_re.finditer(text)})
    for d in dtcs:
        entries.append({'type': 'dtc', 'code': d, 'name': '', 'notes': ''})

    # Look for PID lines: e.g., 'PID: 0C RPM' or 'Parameter,Unit,PID'
    pid_lines = []
    for line in text.splitlines():
        if re.search(r'PID|Parameter|Data Stream|PID Code|PID\s*[:=]', line, re.IGNORECASE):
            pid_lines.append(line.strip())

    # Simple parse of lines containing known PIDs or common PID names
    pid_name_re = re.compile(r'\b(RPM|STFT|LTFT|MAP|MAF|BATTERY|VOLT|O2|THROTTLE)\b', re.IGNORECASE)
    for line in pid_lines:
        codes = dtc_re.findall(line)
        names = pid_name_re.findall(line)
        if codes or names:
            entries.append({'type': 'pid_line', 'line': line, 'codes': codes, 'names': names})

    return entries


def parse_pdf_for_pids(path: str) -> Dict[str, object]:
    text = extract_text_from_pdf(path)
    if not text.strip():
        return {'ok': False, 'error': 'no_text_extracted'}
    entries = extract_pid_entries(text)
    return {'ok': True, 'entries': entries, 'text_snippet': text[:2000]}


def save_pid_db(entries: List[Dict[str, str]], out_path: str = None) -> str:
    base = out_path or os.path.join(os.path.dirname(__file__), '..', 'data', 'pid_db.json')
    base = os.path.abspath(base)
    try:
        # ensure directory exists
        os.makedirs(os.path.dirname(base), exist_ok=True)
        existing = {}
        if os.path.exists(base):
            try:
                with open(base, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
        # merge entries heuristically
        for e in entries:
            if e.get('type') == 'dtc' and 'code' in e:
                existing.setdefault('dtcs', {})[e['code']] = {'name': e.get('name',''), 'notes': e.get('notes','')}
        with open(base, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2)
        return base
    except Exception as ex:
        raise
