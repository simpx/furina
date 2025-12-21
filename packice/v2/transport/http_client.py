import requests
from typing import Any, Dict, Optional, Tuple
from .base import TransportClient

class HttpTransportClient(TransportClient):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def acquire(self, objid: Optional[str], intent: str, ttl: Optional[float] = None, meta: Optional[Dict] = None) -> Tuple[Dict, Any]:
        url = f"{self.base_url}/acquire"
        payload = {
            "objid": objid,
            "intent": intent,
            "ttl_seconds": ttl,
            "meta": meta
        }
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Acquire failed: {resp.text}")
            
        data = resp.json()
        # Handle is the path string
        return data, data['attachment_handle']

    def seal(self, lease_id: str) -> None:
        url = f"{self.base_url}/seal"
        resp = requests.post(url, json={"lease_id": lease_id})
        if resp.status_code != 200:
            raise RuntimeError(f"Seal failed: {resp.text}")

    def release(self, lease_id: str) -> None:
        url = f"{self.base_url}/release"
        resp = requests.post(url, json={"lease_id": lease_id})
        if resp.status_code != 200:
            raise RuntimeError(f"Release failed: {resp.text}")
