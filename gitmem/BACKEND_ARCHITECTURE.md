# GITMEM Backend Architecture

## 1. System Overview
GitMem is a version-controlled, multi-layered memory storage system for AI agents, designed with GitHub-like semantics (commits, branches, forks) and enterprise-grade governance.

## 2. Architecture Diagram

```mermaid
graph TD
    Client[Agent SDK / UI] --> API[API Layer (REST/gRPC)]
    
    subgraph "Core Services"
        API --> Auth[Auth & Governance]
        API --> Repo[Repository Service]
        API --> AgentMgr[Agent Manager]
        API --> Activity[Activity Feed]
    end
    
    subgraph "Storage Engine"
        Repo --> MetaDB[(Metadata DB - Postgres/SQLite)]
        Repo --> ObjectStore[(Blob Store - S3/Local)]
        Repo --> VectorDB[(Vector Store - Chroma/Qdrant)]
        Repo --> GraphDB[(Knowledge Graph - NetworkX/Neo4j)]
    end
    
    subgraph "Processing Pipeline"
        Ingest[Ingestion Worker] --> Index[Indexer]
        Index --> VectorDB
        Index --> GraphDB
        Summarizer[AI Summarizer] --> ObjectStore
    end
    
    Repo --> Ingest
```

## 3. Data Models (Schema)

### 3.1 Memory Object (`MemoryItem`)
```python
class MemoryItem(BaseModel):
    id: str = Field(default_factory=uuid4)
    content: str
    type: Enum("episodic", "semantic", "procedural", "state")
    
    # Metadata
    agent_id: str
    timestamp: datetime
    importance: float = 0.0
    tags: List[str] = []
    
    # Governance
    scope: Enum("private", "shared", "global")
    provenance: str # Hash or sig of author
    
    # Versioning
    commit_hash: str
    parent_hash: Optional[str]
```

### 3.2 Commit Object (`Commit`)
```python
class Commit(BaseModel):
    hash: str # SHA-256
    parent_hash: Optional[str]
    author_id: str
    message: str
    timestamp: datetime
    
    # The snapshot state
    tree_hash: str # Merkle root of memory state
    changed_files: List[str] # List of memory IDs changed
```

### 3.3 Repository Metadata (`Repository`)
```python
class Repository(BaseModel):
    name: str
    owner: str
    visibility: Enum("public", "private")
    
    # Stats
    stars: int
    forks: int
    watchers: int
    
    # Branching
    branches: Dict[str, str] # name -> commit_hash
    default_branch: str = "main"
```

## 4. API Specification (key endpoints)

### Repository
- `GET /repos/{owner}/{repo}` - Get metadata
- `POST /repos/{owner}/{repo}/fork` - Fork repo
- `POST /repos/{owner}/{repo}/star` - Star repo

### Memory Operations
- `POST /memory` - Add memory (auto-commit or staged)
- `GET /memory` - Semantic search / retrieval
- `GET /memory/{id}` - Get specific memory

### Commits
- `POST /commits` - Create commit
- `GET /commits` - List history
- `GET /commits/{sha}` - Get commit details
- `GET /diff/{base}...{head}` - Diff two commits

### Agents
- `POST /agents/heartbeat` - Send heartbeat
- `GET /agents` - List active agents

## 5. Storage Strategy
- **Metadata**: SQLite for MVP, PostgreSQL for Production. Stores relationships, commits, provenance.
- **Vectors**: ChromaDB (local/server). Stores embeddings for semantic search.
- **Blobs**: File System (local) or S3. Stores large memory content, artifacts.

## 6. Security Model
- **Authentication**: Bearer Tokens (JWT).
- **Encryption**: Optional at-rest encryption for "private" scope memories.
- **RBAC**: 
    - `Reader`: Can view public/shared memories.
    - `Writer`: Can add memories, create branches.
    - `Admin`: Can delete repo, manage settings.

## 7. Scalability & Performance
- **Async Ingestion**: Writes are pushed to a queue (Celery/Redis) for vector embedding to avoid blocking.
- **Caching**: Redis cache for frequently accessed semantic queries.
- **Sharding**: Repositories can be sharded by Organization ID.

## 8. Commit DAG & Version Control
We use a Git-like Merkle DAG. 
- Each **Memory** is a blob.
- A **Tree** represents a directory of memories.
- A **Commit** points to a Tree and a Parent Commit.
- **Branches** are mutable pointers to Commits.

## 9. Next Implementation Steps
1. Enhance `models.py` with the full schema.
2. Implement `AgentManager` for heartbeats.
3. specific `RepoService` to handle branches and commits explicitly (moving logic out of simple `MemoryStore`).
4. Build the "Activity Feed" logger.
