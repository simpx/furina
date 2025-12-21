import time
import uuid
from typing import Optional, Any
from ..core.lease import Lease, LeaseMode
from ..core.object import Object

class InMemoryLease(Lease):
    def __init__(self, objid: str, mode: LeaseMode, ttl: Optional[float] = None):
        self._lease_id = str(uuid.uuid4())
        self._objid = objid
        self._mode = mode
        self._ttl = ttl
        self.created_at = time.time()
        self.last_renewed_at = self.created_at
        self.is_active_flag = True

    @property
    def lease_id(self) -> str:
        return self._lease_id

    @property
    def objid(self) -> str:
        return self._objid

    @property
    def mode(self) -> LeaseMode:
        return self._mode

    @property
    def ttl(self) -> Optional[float]:
        return self._ttl

    def is_expired(self) -> bool:
        if not self.is_active_flag:
            return True
        if self._ttl is None:
            return False
        return (time.time() - self.last_renewed_at) > self._ttl

    def renew(self) -> None:
        if self.is_active_flag:
            self.last_renewed_at = time.time()

    def release(self) -> None:
        self.is_active_flag = False
