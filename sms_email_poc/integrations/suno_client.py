"""Minimal Suno.ai integration helper.

Reads `SUNO_API_KEY` and `SUNO_API_URL` from the environment. Saves generated
audio to `sms_email_poc/data/audio/` and returns a dict with `ok` and `path`.
"""
import os
import time
import base64
from pathlib import Path
import requests


OUT_DIR = Path(os.getenv('SUNO_OUTPUT_DIR', Path(__file__).resolve().parents[2] / 'data' / 'audio'))
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _get_config():
    return {
        'key': os.getenv('SUNO_API_KEY', ''),
        'cookie': os.getenv('SUNO_COOKIE', ''),
        'url': os.getenv('SUNO_API_URL', 'https://api.suno.ai/v1/audio'),
        'default_model': os.getenv('SUNO_DEFAULT_MODEL', ''),
        'default_voice': os.getenv('SUNO_DEFAULT_VOICE', ''),
    }


def generate_audio(prompt: str, voice: str | None = None, model: str | None = None, timeout: int = 60) -> dict:
    cfg = _get_config()
    # Use provided voice/model or fall back to environment defaults
    if not voice and cfg.get('default_voice'):
        voice = cfg.get('default_voice')
    if not model and cfg.get('default_model'):
        model = cfg.get('default_model')

    if not cfg.get('key') and not cfg.get('cookie'):
        return {'ok': False, 'error': 'missing_suno_key_or_cookie'}

    headers = {}
    if cfg.get('key'):
        headers['Authorization'] = f"Bearer {cfg['key']}"
    elif cfg.get('cookie'):
        # Accept raw cookie string in SUNO_COOKIE. If it already contains
        # a 'Cookie:' prefix or key=val pairs, send as-is.
        headers['Cookie'] = cfg['cookie']

    payload = {'prompt': prompt}
    if voice:
        payload['voice'] = voice
    if model:
        payload['model'] = model

    try:
        resp = requests.post(cfg['url'], json=payload, headers=headers, timeout=timeout, stream=False)
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    if not resp.ok:
        try:
            return {'ok': False, 'status': resp.status_code, 'detail': resp.json()}
        except Exception:
            return {'ok': False, 'status': resp.status_code, 'text': resp.text}

    ctype = resp.headers.get('Content-Type', '')
    ts = int(time.time())
    # If Suno returns audio directly
    if 'audio' in ctype:
        ext = 'mp3' if 'mpeg' in ctype or 'mp3' in ctype else 'wav'
        path = OUT_DIR / f'audio_{ts}.{ext}'
        try:
            with open(path, 'wb') as f:
                f.write(resp.content)
            return {'ok': True, 'path': str(path), 'content_type': ctype}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # Otherwise expect JSON with base64 audio field
    try:
        j = resp.json()
    except Exception:
        return {'ok': False, 'error': 'unknown_response_format', 'text': resp.text}

    b64 = j.get('audio_base64') or j.get('audio') or j.get('data')
    if not b64:
        return {'ok': False, 'error': 'no_audio_found', 'response': j}

    # If audio field is nested
    if isinstance(b64, dict):
        # common key names
        for k in ('b64', 'base64', 'audio_base64'):
            if k in b64:
                b64 = b64[k]
                break

    try:
        raw = base64.b64decode(b64)
    except Exception as e:
        return {'ok': False, 'error': 'base64_decode_failed', 'detail': str(e)}

    path = OUT_DIR / f'audio_{ts}.mp3'
    try:
        with open(path, 'wb') as f:
            f.write(raw)
        return {'ok': True, 'path': str(path)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
