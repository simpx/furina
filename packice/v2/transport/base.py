from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

class TransportClient(ABC):
    @abstractmethod
    def acquire(self, objid: Optional[str], intent: str, ttl: Optional[float] = None, meta: Optional[Dict] = None) -> Tuple[Dict, Any]:
        """
        Returns (lease_info, blob_handle)
        lease_info should contain 'lease_id', 'objid', etc.
        blob_handle is the path (str) or fd (int).
        """
        pass

    @abstractmethod
    def seal(self, lease_id: str) -> None:
        pass

    @abstractmethod
    def release(self, lease_id: str) -> None:
        pass
