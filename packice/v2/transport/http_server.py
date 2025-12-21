import json
import http.server
import threading
from typing import Optional
from ..core.engine import Engine
from ..core.lease import LeaseMode

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, engine: Engine, *args, **kwargs):
        self.engine = engine
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self.path == '/acquire':
            self.handle_acquire()
        elif self.path == '/seal':
            self.handle_seal()
        elif self.path == '/release':
            self.handle_release()
        else:
            self.send_error(404)

    def handle_acquire(self):
        try:
            length = int(self.headers.get('content-length', 0))
            data = json.loads(self.rfile.read(length))
            
            objid = data.get('objid') # Can be None
            intent = data['intent'] # "create" or "read"
            ttl = data.get('ttl_seconds', 60)
            meta = data.get('meta')

            mode = LeaseMode.CREATE if intent == 'create' else LeaseMode.READ
            
            lease, obj = self.engine.acquire(objid, mode, ttl, meta)
            
            response = {
                "lease_id": lease.lease_id,
                "objid": lease.objid,
                "intent": intent,
                "attachment_handle": obj.blob.get_handle(), # Path for FS
                "ttl_seconds": ttl
            }
            
            self.send_json(200, response)
        except Exception as e:
            self.send_json(400, {"error": str(e)})

    def handle_seal(self):
        try:
            length = int(self.headers.get('content-length', 0))
            data = json.loads(self.rfile.read(length))
            lease_id = data['lease_id']
            
            self.engine.seal(lease_id)
            self.send_json(200, {"status": "sealed"})
        except Exception as e:
            self.send_json(400, {"error": str(e)})

    def handle_release(self):
        try:
            length = int(self.headers.get('content-length', 0))
            data = json.loads(self.rfile.read(length))
            lease_id = data['lease_id']
            
            self.engine.release(lease_id)
            self.send_json(200, {"status": "released"})
        except Exception as e:
            self.send_json(400, {"error": str(e)})

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

class HttpServer:
    def __init__(self, engine: Engine, port: int = 8080):
        self.engine = engine
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        def handler_factory(*args, **kwargs):
            return RequestHandler(self.engine, *args, **kwargs)
        
        self.server = http.server.HTTPServer(('0.0.0.0', self.port), handler_factory)
        print(f"HTTP Server listening on port {self.port}")
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
