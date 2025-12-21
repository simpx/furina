from typing import Any, Dict, Optional, IO
import os
from .transport.base import TransportClient
from .transport.http_client import HttpTransportClient
from .transport.uds_client import UdsTransportClient

class Lease:
    def __init__(self, transport: TransportClient, info: Dict, handle: Any):
        self.transport = transport
        self.info = info
        self.handle = handle
        self.lease_id = info['lease_id']
        self.objid = info['objid']

    def open(self, mode: str = "rb") -> IO:
        """
        Open the blob for reading or writing.
        Returns a file-like object.
        """
        if isinstance(self.handle, int):
            # It's an FD. Duplicate it so the file object doesn't close the original handle
            # which is managed by this Lease object.
            new_fd = os.dup(self.handle)
            return os.fdopen(new_fd, mode)
        elif isinstance(self.handle, str):
            # It's a path
            return open(self.handle, mode)
        else:
            raise ValueError(f"Unknown handle type: {type(self.handle)}")

    def seal(self):
        self.transport.seal(self.lease_id)

    def release(self):
        self.transport.release(self.lease_id)
        # If handle is FD, close it
        if isinstance(self.handle, int):
            try:
                os.close(self.handle)
            except OSError:
                pass

class Client:
    def __init__(self, address: str):
        """
        Initialize Client with an address.
        If address starts with http:// or https://, uses HTTP transport.
        Otherwise, assumes it's a UDS socket path.
        """
        if address.startswith("http://") or address.startswith("https://"):
            self.transport = HttpTransportClient(address)
        else:
            self.transport = UdsTransportClient(address)

    def acquire(self, objid: Optional[str] = None, intent: str = "read", ttl: int = 60, meta: dict = None) -> Lease:
        info, handle = self.transport.acquire(objid, intent, ttl, meta)
        return Lease(self.transport, info, handle)
