# PackIce Design & Implementation

## Objective
Refine the PackIce architecture to achieve better abstraction and decoupling. The goal is to separate the core logic (Peer, Lease, Object) from the implementation details (Storage, Transport), enabling flexible composition of nodes (e.g., HTTP+FS, UDS+Memfd) and easier future extensions (e.g., Redis-based Lease, S3-based Blob).

## Architecture Overview

The system is divided into five distinct layers:

1.  **Core Layer**: The logical heart. Manages resources, state, and lifecycle.
2.  **Storage Layer**: Concrete backends for storage (Blob) and metadata (Lease).
3.  **Transport Layer**: The "Mover". Adapts the Core to network protocols.
4.  **Server Layer**: The "Assembler". Orchestrates components to form a runnable Node.
5.  **Interface Layer**: The "Consumer". Provides user-facing SDK and CLI.

---

## 1. Core Layer (The Logic)

Located in `packice/core/`.

### Peer (`core/peer.py`)
The central coordinator.
- **Role**: Manages the lifecycle of Objects and Leases.
- **API**: `acquire()`, `seal()`, `release()`.
- **Return Values**: Returns `(Lease, Object)` tuples. The `Object` contains raw `Blob`s, which expose low-level **Handles** (e.g., file paths or FDs).
- **Dependency Injection**: Accepts `BlobFactory` and `LeaseFactory` at initialization.

### Object (`core/object.py`)
The unit of management.
- Contains a list of `Blob`s and metadata.
- Manages state: `CREATING` -> `SEALED`.
- **Decoupling**: Holds Blobs but knows nothing about Leases.

### Lease (`core/lease.py`)
Represents the right to access an Object.
- **Decoupling**: Holds `object_id` (string) instead of a direct reference to `Object`.
- **Attributes**: `lease_id`, `object_id`, `access` (READ/CREATE), `ttl`.

### Blob (`core/blob.py`)
Abstracts a contiguous chunk of data.
- **Interface**: `read()`, `write()`, `seal()`, `get_handle()`.
- **Handle**: An opaque identifier (str path or int FD) used by the Transport layer.

---

## 2. Storage Layer (The Backends)

Located in `packice/storage/`.

### Blob Implementations
- **FileBlob (`storage/fs.py`)**: Stores data in a local file system. Handle is the file path.
- **MemBlob (`storage/memory.py`)**: Stores data in memory (using `memfd_create` on Linux or `tempfile` on others). Handle is the file descriptor (FD).

### Lease Implementations
- **MemoryLease (`storage/memory_lease.py`)**: Stores lease state in Python memory. Generates UUIDs internally.

---

## 3. Transport Layer (The Mover)

Located in `packice/transport/`.

**Role**: Adapts the Core Peer to specific network protocols.
**Key Design Principle**: Transports are **Adapters**, not Consumers. They use the `Peer` API directly to get handles and pass them to the client. They do **not** use the SDK Client.

### HTTP Transport (`transport/http_server.py`)
- **Protocol**: JSON over HTTP.
- **Mechanism**: Returns file paths (handles) in JSON.
- **Use Case**: Networked nodes, shared storage (NFS/Volume).

### UDS Transport (`transport/uds_server.py`)
- **Protocol**: JSON over Unix Domain Sockets.
- **Mechanism**: Uses `SCM_RIGHTS` to pass File Descriptors (FDs) between processes.
- **Use Case**: Local high-performance IPC, container sidecars.

---

## 4. Server Layer (The Assembler)

Located in `packice/server/`.

### Node (`server/node.py`)
- **Role**: Encapsulates the logic of assembling a Peer with specific Storage and Transport components.
- **Responsibility**: Handles configuration, initialization, and lifecycle management (start/stop) of the server.

---

## 5. Interface Layer (The Consumer)

Located in `packice/interface/`.

**Role**: Provides the public face of the system.

### SDK (`interface/sdk.py`)
- **Unified Entry Point**: `packice.connect(target)`.
- **Auto-Detection**:
    - `connect()`: Creates a private, isolated in-memory Peer.
    - `connect("memory://name")`: Connects to a shared in-process Peer (DuckDB style).
    - `connect("http://...")`: Connects to a remote HTTP Peer.
    - `connect("/tmp/...")`: Connects to a local UDS Peer.
- **Direct Access**: Can wrap a `Peer` instance directly (`DirectTransportClient`) for zero-overhead in-process usage.

### CLI (`interface/cli.py`)
- **Role**: The command-line interface for starting the server.
- **Usage**: `python -m packice.interface.cli --impl fs --transport http`

---

## Usage Patterns

### 1. In-Process (DuckDB Style)
Ideal for single-process applications or testing. No network overhead.

```python
import packice.interface.sdk as packice

# Private instance
client = packice.connect()

# Shared instance (between modules)
client_a = packice.connect("memory://shared")
client_b = packice.connect("memory://shared")
```

### 2. Multi-Process (Networked)
Ideal for multi-process applications or distributed systems. Requires a Server process.

**Server (Process A):**
```bash
# Start a UDS node with Memory storage
python3 -m packice.interface.cli --impl mem --transport uds --socket /tmp/packice.sock
```

**Client (Process B):**
```python
import packice.interface.sdk as pa
### CLI (`interface/cli.py`)
- **Role**: The command-line interface fon and FD reception transparently
client = packice.connect("/tmp/packice.sock")

le- **Usage**: `pyire(intent="create")
with lease.open("wb") as f
---

## Usage Patterns

### 1. In-Process (DuckDB St
