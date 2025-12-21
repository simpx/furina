import argparse
import os
import time
import sys
from .core.engine import Engine
from .impl.fs_blob import FileBlob
from .impl.mem_blob import MemBlob
from .impl.memory_lease import InMemoryLease
from .transport.http_server import HttpServer
from .transport.uds_server import UdsServer

def main():
    parser = argparse.ArgumentParser(description="PackIce v2 Node")
    parser.add_argument("--impl", choices=["fs", "mem"], default="fs", help="Blob implementation")
    parser.add_argument("--transport", choices=["http", "uds"], default="http", help="Transport protocol")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--socket", default="/tmp/packice.sock", help="UDS socket path")
    parser.add_argument("--data-dir", default="./data", help="Data directory for FS impl")
    
    args = parser.parse_args()

    # 1. Setup Blob Factory
    if args.impl == "fs":
        data_dir = os.path.abspath(args.data_dir)
        os.makedirs(data_dir, exist_ok=True)
        print(f"Using FileBlob implementation in {data_dir}")
        
        def blob_factory(objid: str):
            path = os.path.join(data_dir, objid)
            return FileBlob(path)
            
    elif args.impl == "mem":
        print("Using MemBlob implementation")
        
        def blob_factory(objid: str):
            return MemBlob(objid)
    
    # 2. Setup Lease Factory
    # Currently only InMemoryLease is supported, but this structure allows for future extension
    def lease_factory(objid, mode, ttl):
        return InMemoryLease(objid, mode, ttl)

    # 3. Initialize Engine
    engine = Engine(blob_factory, lease_factory)
    
    # 4. Start Server
    server = None
    if args.transport == "http":
        server = HttpServer(engine, port=args.port)
        server.start()
    elif args.transport == "uds":
        server = UdsServer(engine, socket_path=args.socket)
        server.start()
        
    print("Node started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        if server:
            server.stop()

if __name__ == "__main__":
    main()
