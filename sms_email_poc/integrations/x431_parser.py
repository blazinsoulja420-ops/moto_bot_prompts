"""Parser for simple Launch X431 pasted logs or CSV exports.

This is a minimal parser that extracts DTC codes and common PID values
from either CSV-like lines or free-form text output from the X431.
"""
import re
from typing import Dict, Any


def parse_x431_text(text: str) -> Dict[str, Any]:
    """Return a dict with keys like 'dtcs' (list) and other PIDs if found."""
    dtc_re = re.compile(r'([PCU][0-9]{4})', re.IGNORECASE)
    dtcs = list({m.group(1).upper() for m in dtc_re.finditer(text)})

    # common PIDs we might parse: RPM, STFT, LTFT, MAP, MAF, RPM
    pid_map = {}
    # look for lines like 'RPM: 800' or 'RPM,800'
    for pid in ['RPM', 'STFT', 'LTFT', 'MAP', 'MAF', 'BATTERY', 'VOLT']:
        m = re.search(rf'{pid}[:=,\s]+([-+]?\d+\.?\d*)', text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
            except Exception:
                val = m.group(1)
            pid_map[pid] = val

    # also try CSV rows with key,value
    for line in text.splitlines():
        if ',' in line and ':' not in line:
            parts = [p.strip() for p in line.split(',') if p.strip()]
            if len(parts) >= 2:
                k, v = parts[0].upper(), parts[1]
                if re.match(r'[PCU][0-9]{4}', k):
                    if 'dtcs' not in pid_map:
                        pid_map['dtcs'] = []
                    pid_map['dtcs'].append(k)
                else:
                    try:
                        pid_map[k] = float(v)
                    except Exception:
                        pid_map[k] = v

    # normalize dtcs
    if dtcs:
        pid_map.setdefault('dtcs', []).extend([d for d in dtcs if d not in pid_map.get('dtcs', [])])

    return pid_map
