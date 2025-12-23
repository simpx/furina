# Packice: 解耦与模块化的p2p缓存

本文档旨在介绍 Packice 的核心设计理念、架构抽象及开发指南。

## Part 1: 背景与设计哲学 (The Why & Philosophy)

### 1. 定义
Packice 是一个灵活的、"Batteries-included" 的 P2P 缓存系统。

### 2. 核心痛点
*   **缺乏统一抽象**: 没有统一抽象，容易出错。
*   **开发效率低**: 现有的缓存系统往往耦合严重，传输协议、存储逻辑、缓存逻辑没有很好解耦。基础设施的变更往往导致大量代码重构，难以快速响应业务变化。

### 3. 设计哲学：分层架构 (Layered Architecture)
我们将系统拆分为三个正交的维度，彻底解耦：
*   **怎么存 (Backend)**: 内存、本地文件、共享文件系统、S3...
*   **怎么管 (Peer)**: 负责权限控制、生命周期管理、元数据维护。
*   **怎么交互 (Transport)**: HTTP、UDS (Unix Domain Socket)、Direct (进程内调用)。

---

## Part 2: 核心抽象 (Core Abstractions)

位于 `packice/core/`，这是理解系统的关键。

### 1. Peer (管理者)
*   **角色**: 大脑。
*   **职责**: 管理 Object 的生命周期（创建、封存、过期回收），处理 `acquire` (申请)、`seal` (封存)、`discard` (丢弃)。
*   **特点**: 它不直接处理数据 IO，只负责分发 "许可证" 和 "句柄"。

### 2. Lease (许可证)
*   **角色**: 权限凭证。
*   **职责**: 拥有 Lease 意味着你拥有了对某个 Object 的操作权（读/写/创建）。
*   **关键区分**: 
    *   **Lease TTL**: 租约过期时间（防止客户端死锁）。
    *   **Object TTL**: 数据过期时间（业务数据的生命周期）。

### 3. Object (对象)
*   **角色**: 数据的逻辑单元。
*   **职责**: 包含元数据 (Meta) 和数据块 (Blob)。
*   **状态机**: `CREATING` -> `SEALED`。

### 4. Blob (数据块)
*   **角色**: 数据的物理载体。
*   **多态性**: `MemBlob` (内存), `FileBlob` (本地文件), `SharedFSBlob` (共享文件)。
*   **特点**: **View 与 Blob 的分离**。
    *   **Server 端**: 管理 Blob (Header, TTL, Sealing)。
    *   **Client 端**: 只持有 View (Read/Write)，互不干扰。

---

## Part 3: 核心流程 (The Workflow)

以 "Client A 创建 -> Client B 读取" 为例：

1.  **Connect**: 
    *   `client = packice.connect("protocol://...")` (自动适配 Transport)。
2.  **Acquire (Create)**:
    *   Client 发送请求 -> Transport 解析 -> Peer 分配 Lease -> Peer 创建空的 Object/Blob -> 返回 Object/Lease -> Transport 解析 -> client 拿到响应
3.  **IO (Write)**:
    *   Client 收到响应 -> 解析 Blob 信息 -> 实例化对应的 `BlobView` (如 `SharedFSBlobView`)。
    *   Client 通过 `BlobView` 直接写入数据。
    *   *优势*: 绕过 Peer，实现 **Zero-copy** (如 `mmap`) 或 **Direct IO**，最大化吞吐量。
4.  **Seal**:
    *   Client 写完 -> 调用 `seal()` -> Peer 修改元数据 (标记为不可变) -> Object 可被他人读取。
5.  **Acquire (Read)**:
    *   Client B 请求 -> Peer 检查权限 -> Peer 分配 Read Lease -> 返回只读 Handle。
    *   Client B 解析 Blob 信息 -> 实例化对应的 `BlobView`。
    *   Client B 通过 `BlobView` 直接读取数据 (Zero-copy/Direct IO)。

---

## Part 4: 进阶流程 (Tiered Storage)

Packice 的架构设计以 `Peer` 为核心交互单元。利用其强大的组合性 (Composability)，我们可以将多个基础 Peer 封装为一个复合 Peer，从而实现复杂的存储策略。以 **TieredPeer (Memory + Disk)** 为例，它作为协调者管理着 Hot Peer (内存) 与 Cold Peer (磁盘) 之间的数据流转与生命周期。以下是分级存储的具体实现流程：

1.  **Write**:
    *   Client 请求写入 -> TieredPeer 优先在 **Hot Peer (Memory)** 分配空间 -> Client 极速写入内存。
2.  **Eviction (后台)**:
    *   内存满了 -> TieredPeer 触发驱逐策略 (LRU)。
    *   TieredPeer 将数据从 **Hot Peer** 搬运到 **Cold Peer (Disk)**。
    *   更新元数据指向 Cold Peer。
3.  **Read (Hit Hot)**:
    *   Client 请求 -> TieredPeer 发现数据在 Hot Peer -> 返回内存 Object -> Client 极速读取。
4.  **Read (Hit Cold)**:
    *   Client 请求 -> TieredPeer 发现数据在 Cold Peer -> 返回文件 Object -> Client 读取磁盘。
    *   *(可选路径)*: TieredPeer 异步将数据先预热回 Hot Peer，再返回 Hot Peer 里的内存 Object

---

## Part 5: 代码地图 (Code Map)

"如果我要加功能，我该改哪里？"

### 目录结构
*   `packice/core/`: 核心接口 (Peer, Blob, Lease)。
*   `packice/backends/`: Blob和Lease在不同系统中的实现 (Memory, FS, SharedFS)。
*   `packice/peers/`: Peer 逻辑实现 (MemoryPeer, SharedFSPeer)。
*   `packice/transport/`: 协议适配 (HTTP, UDS, Direct)。
*   `packice/interface/`: 用户接口 (Client, CLI)。

### 扩展场景指南

#### 场景 A: "我想支持把数据存到 S3 上"
*   **去哪里**: `packice/backends/`
*   **做什么**: 继承 `Blob` 实现 `S3Blob`。

#### 场景 B: "我想用 gRPC 替换 HTTP"
*   **去哪里**: `packice/transport/`
*   **做什么**: 实现 `GrpcServer` 和 `GrpcTransport`，调用现有的 `Peer` 接口。

#### 场景 C: "我想实现一个冷热分级缓存策略"
*   **去哪里**: `packice/peers/`
*   **做什么**: 像 `TieredPeer` 一样，组合两个现有的 Peer，在这一层写调度逻辑。

---

## Part 6: 演示与体验 (Demo & DX)

展示 `examples/shared_fs_demo.py` 的代码片段，强调易用性：

```python
# 1. 极简的连接方式 (自动识别协议)
client = packice.connect(peer)

# 2. Pythonic 的资源管理 (Context Manager)
# 自动处理关闭和异常
with client.create(meta={"ttl": 60}) as obj:
    obj.write(b"Hello Packice")
    # 3. 显式封存
    obj.seal()

# 4. 像操作本地对象一样读取
with client.get(obj.id) as obj:
    print(obj.buffer.tobytes())
```

---

## Q&A 准备

*   **Q: 为什么要区分 Lease TTL 和 Object TTL？**
    *   A: Lease 是为了防止死锁（比如客户端挂了没释放锁），Object TTL 是业务数据的生命周期。
*   **Q: 为什么 Client 写数据不经过 Peer？**
    *   A: 为了性能。Peer 只负责控制面（Control Plane），数据面（Data Plane）应该尽可能直接（Zero-copy, Direct IO）。
*   **Q: SharedFS 和普通 FS 有什么区别？**
    *   A: SharedFS 假设多个进程/节点挂载了同一个目录，所以它需要处理跨进程的 Header 同步、锁管理以及基于文件 mtime 的 GC。
