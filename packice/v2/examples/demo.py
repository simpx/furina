import os
import sys
import time
from ..sdk import Client

def run_demo(address: str, name: str):
    print(f"\n{'='*20} Running Demo: {name} {'='*20}")
    print(f"Connecting to: {address}")
    
    try:
        client = Client(address)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 1. Create Object
    print("\n--- 1. Create Object ---")
    try:
        lease = client.acquire(intent="create", ttl=60)
        objid = lease.objid
        print(f"Acquired lease: {lease.lease_id}")
        print(f"Generated ObjID: {objid}")
        
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
    print(f"\n--- 2. Read Object {objid} ---")
    try:
        read_lease = client.acquire(objid, intent="read")
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
    # Check if servers are running (simple check by socket/port existence would be better, 
    # but here we just assume user followed instructions)
    
    print("Note: Ensure you have started the servers in separate terminals:")
    print("  1. python3 -m packice.v2.main --impl fs --transport http --port 8080")
    print("  2. python3 -m packice.v2.main --impl mem --transport uds --socket /tmp/packice.sock")
    print("Waiting 2 seconds...")
    time.sleep(2)

    # Demo 1: HTTP + FS
    run_demo("http://localhost:8080", "HTTP + FS")

    # Demo 2: UDS + Memfd
    run_demo("/tmp/packice.sock", "UDS + Memfd")

if __name__ == "__main__":
    main()
