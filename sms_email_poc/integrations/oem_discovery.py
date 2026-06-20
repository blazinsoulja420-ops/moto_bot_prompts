"""OEM manual discovery helpers.

This module provides non-autonomous discovery of likely OEM/manual URLs
based on make/model/year. It DOES NOT download paywalled content without
explicit permission; use `candidate_manuals()` to get candidates and
`fetch_manual()` with `allow_download=True` to attempt retrieval.
"""
import requests
from typing import List, Dict, Any, Optional


def candidate_manuals(make: str, model: str, year: str) -> List[Dict[str, Any]]:
    """Return a short list of candidate manual URLs to inspect.

    This is a heuristic list of common patterns; it does not guarantee
    the manuals are freely available.
    """
    if not make:
        return []
    make_l = (make or '').lower()
    candidates = []
    # Official owner manual pages (common pattern)
    candidates.append({
        'source': 'manufacturer_owner',
        'url': f'https://www.{make_l}.com/support/owner-manuals',
        'note': 'Manufacturer owner manual support page (may vary by brand domain)'
    })
    # Third-party common manual host
    candidates.append({
        'source': 'third_party',
        'url': f'https://www.manualslib.com/search.php?q={make}+{model}+{year}',
        'note': 'ManualsLib search result'
    })
    # Generic service manual marketplaces (may be paywalled)
    candidates.append({
        'source': 'service_manual_market',
        'url': f'https://www.tradebit.com/filedetail.php/4461230-{make}-{model}-service-manual',
        'note': 'Sample marketplace URL (pattern only)'
    })
    return candidates


def fetch_manual(url: str, allow_download: bool = False, timeout: int = 15) -> Dict[str, Any]:
    """Inspect a URL and optionally attempt to download the target.

    Returns metadata including HTTP status and a short content-type. If
    `allow_download` is True and the response looks like a PDF, the 'content'
    key will contain bytes; otherwise content is None.
    """
    try:
        head = requests.head(url, timeout=timeout, allow_redirects=True)
        status = head.status_code
        ctype = head.headers.get('Content-Type', '')
    except Exception:
        # fallback to GET for servers that don't respond to HEAD
        try:
            r = requests.get(url, timeout=timeout)
            status = r.status_code
            ctype = r.headers.get('Content-Type', '')
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    result = {'ok': True, 'status': status, 'content_type': ctype}
    if allow_download and status == 200 and 'pdf' in (ctype or '').lower():
        r = requests.get(url, timeout=timeout)
        if r.ok:
            result['content'] = r.content
        else:
            result['ok'] = False
            result['error'] = f'Failed to download: {r.status_code}'
    return result
