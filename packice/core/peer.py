import uuid
import time
from typing import Dict, Optional, Callable, Any, Tuple
from .object import Object, ObjectState
from .lease import Lease, AccessType
from .blob import Blob

BlobFactory = Callable[[str], Blob]  # object_id -> Blob
LeaseFactory = Callable[[str, AccessType, Optional[float]], Lease] # object_id, access, ttl -> Lease

class Peer:
    def __init__(self, blob_factory: BlobFactory, lease_factory: LeaseFactory):
        self.blob_factory = blob_factory
        self.lease_factory = lease_factory
        self.objects: Dict[str, Object] = {}
        self.leases: Dict[str, Lease] = {}

    def acquire(self, object_id: Optional[str], access: AccessType, ttl: Optional[float] = None, meta: Optional[Dict[str, Any]] = None) -> Tuple[Lease, Object]:
        # Check for expiration of existing leases first (lazy cleanup)
        self._cleanup_expired_leases()

        if object_id is None:
            if access == AccessType.READ:
                raise ValueError("Cannot acquire read lease without object_id")
            object_id = str(uuid.uuid4())

        obj = self.objects.get(object_id)

        if access == AccessType.CREATE:
            if obj is not None:
                # If object exists, we can't create it again unless it's a "restart" or we handle it.
                # For simplicity, if it exists, fail.
                raise ValueError(f"Object {object_id} already exists")
            
            # Create new object
            # For CREATE, we create the first blob
            blob = self.blob_factory(object_id)
            obj = Object(object_id, [blob], meta)
            self.objects[object_id] = obj
        
        elif access == AccessType.READ:
            if obj is None:
                raise KeyError(f"Object {object_id} not found")
            if not obj.is_sealed():
                # Can we read while creating? 
                # v0 design says: "Objects are writable only while in CREATING... SEALED objects are immutable."
                # Usually read is allowed on SEALED.
                # If it's CREATING, maybe we can't read yet?
                # v0: "For read intent, may fail if the node lacks a sealed copy"
                raise ValueError(f"Object {object_id} is not sealed yet")

        lease = self.lease_factory(object_id, access, ttl)
        self.leases[lease.lease_id] = lease
        
        # Return lease and the object
        return lease, obj

    def seal(self, lease_id: str):
        lease = self._get_active_lease(lease_id)
        if lease.access != AccessType.CREATE:
            raise ValueError("Cannot seal a read lease")
        
        obj = self.objects.get(lease.object_id)
        if obj is None:
             raise KeyError(f"Object {lease.object_id} not found for lease {lease_id}")

        obj.seal()
        # In a real system, we might notify waiting readers here

    def release(self, lease_id: str):
        if lease_id not in self.leases:
            return
        lease = self.leases[lease_id]
        lease.release()
        del self.leases[lease_id]
        
        # Check if object should be evicted?
        # For now, we keep it.

    def _get_active_lease(self, lease_id: str, raise_error=True) -> Lease:
        lease = self.leases.get(lease_id)
        if lease and lease.is_expired():
            self.release(lease_id)
            lease = None
        
        if lease is None:
            if raise_error:
                raise KeyError(f"Lease {lease_id} not found or expired")
            return None
        return lease

    def _cleanup_expired_leases(self):
        # Simple lazy cleanup
        expired = [lid for lid, l in self.leases.items() if l.is_expired()]
        for lid in expired:
            self.release(lid)
