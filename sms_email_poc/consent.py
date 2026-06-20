"""Simple in-memory consent token manager for remote actions.

Used to create short-lived consent tokens that must be confirmed by the
vehicle owner before remote actions (like launching TeamViewer/diagnose)
are performed.
"""
import time
import uuid
from typing import Dict, Any, Optional

# token -> (expires_at, payload)
_STORE: Dict[str, tuple[float, Dict[str, Any]]] = {}


def create_consent(payload: Dict[str, Any], ttl: int = 300) -> str:
    token = uuid.uuid4().hex[:8]
    _STORE[token] = (time.time() + ttl, payload)
    return token


def verify_consent(token: str) -> Optional[Dict[str, Any]]:
    rec = _STORE.get(token)
    if not rec:
        return None
    expires_at, payload = rec
    if time.time() > expires_at:
        del _STORE[token]
        return None
    # one-time use
    del _STORE[token]
    return payload
