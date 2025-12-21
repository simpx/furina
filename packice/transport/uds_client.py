import socket
import json
import os
import array
from typing import Any, Dict, Optional, Tuple, List
from .base import TransportClient

class UdsTransportClient(TransportClient):
    def __init__(self, socket_path: str):
        self.socket_path = socket_path

    def _connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        return sock

    def _recv_fds(self, sock, msglen, maxfds):
        fds = array.array("i")
        msg, ancdata, flags, addr = sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
                fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
        return msg, list(fds)

    def acquire(self, object_id: Optional[str], intent: str, ttl: Optional[float] = None, meta: Optional[Dict] = None) -> Tuple[Dict, List[Any]]:
        sock = self._connect()
        try:
            req = {
                "command": "acquire",
                "object_id": object_id,
                "intent": intent,
                "ttl_seconds": ttl,
                "meta": meta
            }
            sock.sendall(json.dumps(req).encode('utf-8'))
            
            # Assume max 16 FDs for now
            msg, fds = self._recv_fds(sock, 4096, 16)
            resp = json.loads(msg.decode('utf-8'))
            
            if resp.get("status") == "error":
                raise RuntimeError(resp.get("message"))
                
            handles = []
            if fds:
                handles = fds
            else:
                handles = resp.get("handles", [])
                
            return resp, handles
        finally:
            sock.close()

    def seal(self, lease_id: str) -> None:
        sock = self._connect()
        try:
            req = {"command": "seal", "lease_id": lease_id}
            sock.sendall(json.dumps(req).encode('utf-8'))
            resp = json.loads(sock.recv(4096).decode('utf-8'))
            if resp.get("status") == "error":
                raise RuntimeError(resp.get("message"))
        finally:
            sock.close()

    def release(self, lease_id: str) -> None:
        sock = self._connect()
        try:
            req = {"command": "release", "lease_id": lease_id}
            sock.sendall(json.dumps(req).encode('utf-8'))
            resp = json.loads(sock.recv(4096).decode('utf-8'))
            if resp.get("status") == "error":
                raise RuntimeError(resp.get("message"))
        finally:
            sock.close()
