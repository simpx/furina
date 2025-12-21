import os
import sys
import time
from ..sdk import Client
from ..core.peer import Peer
from ..impl.mem_blob import MemBlob
from ..impl.memory_lease import MemoryLease

def demo_in_process():
    print(f"\n{'='*20} Running Demo: In-Process (Direct) {'='*20}")
    
    # 1. Setup Peer (In-Memory)
    print("Initializing Peer with MemBlob and MemoryLease...")
    def blob_factory(oid): return MemBlob(oid)
    def lease_factory(oid, access, ttl): return MemoryLease(oid, access, ttl)
    peer = Peer(blob_factory, lease_factory)
    
    # 2. Use SDK with Peer instance
    client = Client(peer)
    
    # 3. Create Object
    print("\n--- Create Object ---")
    lease = client.acquire(intent="create")
    object_id = lease.object_id
    print(f"Acquired lease: {lease.lease_id} for object {object_id}")
    
    with lease.open("wb") as f:
        f.write(b"Hello In-Process!")
    lease.seal()
    lease.release()
    
    # 4. Read Object
    print(f"\n--- Read Object {object_id} ---")
    lease = client.acquire(object_id=object_id, intent="read")
    with lease.open("rb") as f:
        data = f.read()
        print(f"Read data: {data}")
    lease.release()

def run_demo(target: str, name: str):
    print(f"\n{'='*20} Running Demo: {name} {'='*20}")
    print(f"Connecting to: {target}")
    
    try:
        client = Client(target)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 1. Create Object
    print("\n--- 1. Create Object ---")
    try:
        lease = client.acquire(intent="create", ttl=60)
        object_id = lease.object_id
        print(f"Acquired lease: {lease.lease_id}")
        print(f"Generated Object ID: {object_id}")
        
        # Write data using the unified open() interface
        print("Writing data...")
        with lease.open("wb") as f:
            f.write(f"Hello from {name}!".encode('utf-8'))
        
        print("Sealing object...")
        lease.seal()
        
        print("Releasing lease...")
        lease.release()
        
    except Exception as e:
        print(f"Error during create flow: {e}")
        return

    # 2. Read Object
    print(f"\n--- 2. Read Object {object_id} ---")
    try:
        read_lease = client.acquire(object_id, intent="read")
        print(f"Acquired read lease: {read_lease.lease_id}")
        
        # Read data using the unified open() interface
        print("Reading data...")
        with read_lease.open("rb") as f:
            content = f.read()
            print(f"Content: {content.decode('utf-8')}")
            
        print("Releasing read lease...")
        read_lease.release()
        
    except Exception as e:
        print(f"Error during read flow: {e}")

def main():
    # Demo 1: In-Process
    demo_in_process()

    # Check if servers are running
    print("\nNote: For Networked demos, ensure you have started the servers:")
    print("  1. python3 -m packice.v2.main --impl fs --transport http --port 8080")
    print("  2. python3 -m packice.v2.main --impl mem --transport uds --socket /tmp/packice.sock")
    print("Waiting 2 seconds...")
    time.sleep(2)

    # Demo 2: HTTP + FS
    run_demo("http://localhost:8080", "HTTP + FS")

    # Demo 3: UDS + Memfd
    run_demo("/tmp/packice.sock", "UDS + Memfd")

if __name__ == "__main__":
    main()
