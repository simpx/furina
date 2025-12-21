import socket
import os
import json
import struct
import threading
import array
from typing import Optional, List
from ..core.peer import Peer
from ..core.lease import AccessType

class UdsServer:
    def __init__(self, peer: Peer, socket_path: str = "/tmp/packice.sock"):
        self.peer = peer
        self.socket_path = socket_path
        self.server_socket = None
        self.running = False
        self.thread = None

    def start(self):
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(5)
        self.running = True
        
        print(f"UDS Server listening on {self.socket_path}")
        self.thread = threading.Thread(target=self._accept_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, _ = self.server_socket.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(client_sock,))
                client_thread.daemon = True
                client_thread.start()
            except OSError:
                break

    def _handle_client(self, sock: socket.socket):
        # Simple protocol: Read one line (JSON), send one line (JSON) + optional FD
        # In a real persistent connection, we'd loop.
        # For v2 POC, let's assume one request per connection or loop until close.
        try:
            with sock:
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                    
                    try:
                        req = json.loads(data.decode('utf-8'))
                        self._process_request(sock, req)
                    except json.JSONDecodeError:
                        self._send_error(sock, "Invalid JSON")
                        break
                    except Exception as e:
                        self._send_error(sock, str(e))
                        break
        except Exception as e:
            print(f"Client handler error: {e}")

    def _process_request(self, sock: socket.socket, data: dict):
        cmd = data.get('command')
        
        if cmd == 'acquire':
            object_id = data.get('object_id') # Can be None
            intent = data['intent']
            ttl = data.get('ttl_seconds') # Optional for UDS, maybe connection bound?
            meta = data.get('meta')
            
            access = AccessType.CREATE if intent == 'create' else AccessType.READ
            lease, obj = self.peer.acquire(object_id, access, ttl, meta)
            
            resp = {
                "status": "ok",
                "lease_id": lease.lease_id,
                "object_id": lease.object_id
            }
            
            # Check if we need to pass FDs
            handles = [b.get_handle() for b in obj.blobs]
            fds = []
            paths = []
            
            for h in handles:
                if isinstance(h, int):
                    fds.append(h)
                else:
                    paths.append(h)
            
            if fds:
                self._send_response_with_fds(sock, resp, fds)
            else:
                resp["handles"] = paths
                self._send_response(sock, resp)

        elif cmd == 'seal':
            lease_id = data['lease_id']
            self.peer.seal(lease_id)
            self._send_response(sock, {"status": "sealed"})

        elif cmd == 'release':
            lease_id = data['lease_id']
            self.peer.release(lease_id)
            self._send_response(sock, {"status": "released"})
        
        else:
            self._send_error(sock, "Unknown command")

    def _send_response(self, sock: socket.socket, data: dict):
        msg = json.dumps(data).encode('utf-8')
        sock.sendall(msg)

    def _send_error(self, sock: socket.socket, msg: str):
        self._send_response(sock, {"status": "error", "message": msg})

    def _send_response_with_fds(self, sock: socket.socket, data: dict, fds: List[int]):
        msg = json.dumps(data).encode('utf-8')
        ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))]
        sock.sendmsg([msg], ancillary)
