from enum import Enum
from typing import Dict, Optional, Any
from .blob import Blob

class ObjectState(Enum):
    CREATING = "CREATING"
    SEALED = "SEALED"

class Object:
    def __init__(self, objid: str, blob: Blob, meta: Optional[Dict[str, Any]] = None):
        self.objid = objid
        self.blob = blob
        self.meta = meta or {}
        self.state = ObjectState.CREATING
        self.sealed_size: Optional[int] = None

    def seal(self):
        if self.state == ObjectState.SEALED:
            return
        self.blob.seal()
        self.state = ObjectState.SEALED
        # In a real implementation, we might want to get the size from the blob
        # self.sealed_size = ... 

    def is_sealed(self) -> bool:
        return self.state == ObjectState.SEALED
