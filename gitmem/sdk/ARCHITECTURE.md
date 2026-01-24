# GITMEM SDK Architecture

## Overview
The GITMEM SDK is a layered architecture designed to bridge autonomous agents with the version-controlled memory core. It follows a modular design to support extensibility and multiple storage backends.

## Architecture Layers

### 1. Interface Layer (Top interactions)
- **`GitMem` Client**: The main entry point. Singleton-ready, thread-safe.
- **`Memory` Abstractions**: High-level classes (`WorkingMemory`, `EpisodicMemory`, etc.) that agents interact with directly.
- **`CLI`**: Command-line interface wrapping the SDK.

### 2. Logic & Control Layer (Middleware)
- **`MemoryController`**: Orchestrates data flow between short-term and long-term stores.
- **`Pipeline`**: Customizable processing chain for incoming memories (e.g., PII Redaction -> Summarization -> Embedding).
- **`ContextManager`**: Utilities for packing memories into LLM context windows (token counting, ranking).

### 3. Data & Transport Layer
- **`TransportAdapter`**: Abstract base class for communication (HTTP, RPC, Local Direct).
- **`Serializer`**: Handles JSON/MsgPack serialization of complex Agent States.

## Component Design

### Memory Types (Models)
The SDK provides strict Pydantic models for different memory types:

*   **`CoreMemory`**: Base class with `id`, `timestamp`, `provenance`.
*   **`EpisodicMemory`**: Events, observations (Time-series).
*   **`SemanticMemory`**: Facts, knowledge (Vector-indexed).
*   **`ProceduralMemory`**: Skills, code snippets (Graph/Execution-indexed).
*   **`AgentState`**: Snapshot of internal variables/stack.

### Versioning Flow
1.  **Stage**: `client.add()` -> Adds to local staging / working memory.
2.  **Commit**: `client.commit()` -> Flushes staging to persistent storage, creates a Merkle node.
3.  **Branch**: `client.checkout(branch)` -> Switches the "HEAD" pointer of the agent's memory.

## Security & Governance
*   **Encryption**: Optional client-side field-level encryption before transport.
*   **RBAC**: memory scopes (`private`, `shared`, `global`) enforced at the API level.

## Extensibility
*   **Plugins**: The SDK supports plugins for different Vector DBs (when running in local mode) or custom ranking algorithms.
