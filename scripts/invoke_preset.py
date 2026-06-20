"""Invoke a named preset and print its content.

Usage:
  python scripts/invoke_preset.py music-producer

This helper reads `prompts/aliases.json` and prints the referenced file.
Other scripts can call it or import `prompts.preset_loader` for programmatic use.
"""
import sys
from pathlib import Path
import json


def load_alias(alias: str) -> str:
    root = Path(__file__).resolve().parents[1]
    aliases_file = root / 'aliases.json'
    if not aliases_file.exists():
        raise SystemExit('aliases.json not found')
    aliases = json.loads(aliases_file.read_text(encoding='utf-8'))
    if alias not in aliases:
        raise SystemExit(f'alias not found: {alias}')
    preset_path = root / aliases[alias]
    if not preset_path.exists():
        raise SystemExit(f'preset file missing: {preset_path}')
    return preset_path.read_text(encoding='utf-8')


def main(argv):
    if len(argv) < 1:
        print('Usage: python scripts/invoke_preset.py <alias>')
        return 2
    alias = argv[0]
    content = load_alias(alias)
    print(content)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
