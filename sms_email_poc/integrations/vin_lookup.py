"""VIN lookup helpers using NHTSA Vehicle API."""
import requests
from typing import Dict, Any, Optional


NHTSA_DECODE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json"


def decode_vin(vin: str) -> Optional[Dict[str, Any]]:
    """Decode VIN using NHTSA API. Returns dict of parsed fields or None on error."""
    if not vin or len(vin) < 11:
        return None
    try:
        url = NHTSA_DECODE_URL.format(vin=vin)
        resp = requests.get(url, timeout=10)
        if not resp.ok:
            return None
        data = resp.json()
        results = data.get('Results') or []
        if not results:
            return None
        # Convert list of result dicts into a simpler mapping (take first)
        res = results[0]
        out = {
            'Make': res.get('Make'),
            'Model': res.get('Model'),
            'ModelYear': res.get('ModelYear'),
            'Manufacturer': res.get('Manufacturer'),
            'VIN': res.get('VIN') or vin,
            'Trim': res.get('Trim'),
            'PlantCountry': res.get('PlantCountry'),
        }
        return out
    except Exception:
        return None
