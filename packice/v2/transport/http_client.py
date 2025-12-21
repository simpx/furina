import requests
from typing import Any, Dict, Optional, Tuple, List
from .base import TransportClient

class HttpTransportClient(TransportClient):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def acquire(self, object_id: Optional[str], intent: str, ttl: Optional[float] = None, meta: Optional[Dict] = None) -> Tuple[Dict, List[Any]]:
        url = f"{self.base_url}/acquire"
        payload = {
            "object_id": object_id,
            "intent": intent,
            "ttl_seconds": ttl,
            "meta": meta
        }
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Acquire failed: {resp.text}")
            
        data = resp.json()
        # Handles are paths
        return data, data['handles']

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
