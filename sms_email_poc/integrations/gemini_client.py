"""Lightweight Gemini multimodal client wrapper.

This module provides a small helper to send an image (+ optional text)
to a Gemini-compatible HTTP endpoint. It reads `GEMINI_API_KEY` and
`GEMINI_API_URL` from the environment. The repository does NOT store
API keys; set them in your shell or .env instead.

Usage: set `GEMINI_API_KEY` and `GEMINI_API_URL` (e.g. the Google Cloud
endpoint) and call `analyze_image(image_path, prompt)`.
"""
import os
from typing import Optional, Dict, Any
import requests


def _get_config() -> Dict[str, str]:
    return {
        'key': os.getenv('GEMINI_API_KEY', ''),
        'url': os.getenv('GEMINI_API_URL', ''),
    }


def analyze_image(image_path: str, prompt: Optional[str] = None, timeout: int = 30) -> Optional[Dict[str, Any]]:
    """Send `image_path` and optional `prompt` to the Gemini endpoint.

    Returns parsed JSON on success, or None if not configured or on error.
    """
    cfg = _get_config()
    if not cfg['key'] or not cfg['url']:
        return None

    headers = {
        'Authorization': f'Bearer {cfg['key']}',
    }

    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'prompt': prompt or ''}
            resp = requests.post(cfg['url'], headers=headers, files=files, data=data, timeout=timeout)
        if not resp.ok:
            return {'error': f'HTTP {resp.status_code}', 'text': resp.text}
        try:
            return resp.json()
        except Exception:
            return {'text': resp.text}
    except Exception as e:
        return {'error': str(e)}
