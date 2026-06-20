"""Safe helper to store secrets in a local .env file.

Usage:
  python scripts/store_env_key.py GEMINI_API_KEY "your-key-here"

This writes the given key to `.env` in the project root, preserving any
existing values and creating the file if needed. The file is added to
`.gitignore` by default in this repo; the script will not commit anything.
"""
import os
import sys
from pathlib import Path


def load_env(path: Path) -> dict:
    res = {}
    if not path.exists():
        return res
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.strip().startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            res[k.strip()] = v.strip().strip('"').strip("'")
    return res


def write_env(path: Path, data: dict) -> None:
    lines = []
    for k, v in data.items():
        lines.append(f'{k}="{v}"')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def ensure_gitignore(root: Path) -> None:
    gitignore = root / '.gitignore'
    if not gitignore.exists():
        gitignore.write_text('.env\n', encoding='utf-8')
        return
    text = gitignore.read_text(encoding='utf-8')
    if '.env' not in text:
        gitignore.write_text(text + '\n.env\n', encoding='utf-8')


def main(argv):
    # argv is sys.argv[1:]; expect KEY and VALUE
    if len(argv) < 2:
        print('Usage: python scripts/store_env_key.py KEY_NAME "value"')
        return 2
    key = argv[0]
    value = argv[1]
    root = Path(__file__).resolve().parents[2]
    env_path = root / '.env'
    env = load_env(env_path)
    env[key] = value
    write_env(env_path, env)
    ensure_gitignore(root)
    print(f'Wrote {key} to {env_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
