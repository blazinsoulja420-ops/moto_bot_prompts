"""Programmatic loader for prompt presets by alias.

Import and call `load_preset('music-producer')` to get the preset text.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALIASES = ROOT / 'aliases.json'


def load_preset(alias: str) -> str:
    if not ALIASES.exists():
        raise FileNotFoundError('prompts/aliases.json not found')
    aliases = json.loads(ALIASES.read_text(encoding='utf-8'))
    if alias not in aliases:
        raise KeyError(f'alias not registered: {alias}')
    fp = ROOT / aliases[alias]
    if not fp.exists():
        raise FileNotFoundError(f'preset file missing: {fp}')
    return fp.read_text(encoding='utf-8')
