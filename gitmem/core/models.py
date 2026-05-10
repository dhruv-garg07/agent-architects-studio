"""
GitMem v2.0 — Core Data Models

All Pydantic models for the 6-layer architecture.
Workspace-first, event-driven, cloud-native.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, model_validator
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ============================================================
# Enums
# ============================================================

class Visibility(str, Enum):
    PRIVATE = "private"
    WORKSPACE = "workspace"
    PUBLIC = "public"


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    STATE = "state"


class MergePolicy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    IMPORTANCE_PRIORITY = "importance_priority"
    SEMANTIC_MERGE = "semantic_merge"
    MANUAL_CONFLICT = "manual_conflict"


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class RepoRole(str, Enum):
    ADMIN = "admin"
    WRITER = "writer"
    READER = "reader"


class RefType(str, Enum):
    BRANCH = "branch"
    TAG = "tag"
    AGENT = "agent"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class EventType(str, Enum):
    # Memory events
    MEMORY_CREATED = "MEMORY_CREATED"
    MEMORY_UPDATED = "MEMORY_UPDATED"
    MEMORY_DELETED = "MEMORY_DELETED"
    # Commit events
    COMMIT_CREATED = "COMMIT_CREATED"
    # Branch events
    BRANCH_CREATED = "BRANCH_CREATED"
    BRANCH_DELETED = "BRANCH_DELETED"
    # VCS events
    MERGE_COMPLETED = "MERGE_COMPLETED"
    CHERRY_PICK_COMPLETED = "CHERRY_PICK_COMPLETED"
    ROLLBACK_EXECUTED = "ROLLBACK_EXECUTED"
    # Collaboration events
    COLLAB_ADDED = "COLLAB_ADDED"
    COLLAB_REMOVED = "COLLAB_REMOVED"
    # Repo events
    REPO_CREATED = "REPO_CREATED"
    REPO_FORKED = "REPO_FORKED"
    # Infra events
    COMPACTION_RUN = "COMPACTION_RUN"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"


# ============================================================
# LAYER 3 — Workspace & Access Models
# ============================================================

class Workspace(BaseModel):
    workspace_id: str = Field(default_factory=generate_uuid)
    name: str
    slug: str
    owner_id: str
    plan: Literal["free", "pro", "enterprise"] = "free"
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class WorkspaceMember(BaseModel):
    workspace_id: str
    user_id: str
    role: WorkspaceRole = WorkspaceRole.MEMBER
    invited_by: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.now)


class Repo(BaseModel):
    repo_id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    name: str
    slug: str
    description: str = ""
    visibility: Visibility = Visibility.PRIVATE
    owner_id: str
    default_branch: str = "main"
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Collaborator(BaseModel):
    repo_id: str
    user_id: str
    role: RepoRole = RepoRole.READER
    invited_by: str
    accepted: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# LAYER 4 — Version Control Models
# ============================================================

class MemoryItem(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    repo_id: str
    workspace_id: str
    agent_id: str
    type: MemoryType = MemoryType.EPISODIC
    content: str
    importance: float = 0.0
    tags: List[str] = Field(default_factory=list)
    visibility: Visibility = Visibility.PRIVATE
    provenance: Optional[str] = None
    commit_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage/indexing (excludes embedding)."""
        res = self.model_dump(mode='json', exclude={'embedding'})
        res['agent_id'] = self.agent_id
        res['type'] = self.type.value if hasattr(self.type, 'value') else str(self.type)
        return res

    @model_validator(mode='before')
    @classmethod
    def backcompat_scope(cls, data: Any) -> Any:
        """Migrate old 'scope' field to 'visibility'."""
        if isinstance(data, dict):
            if 'scope' in data and 'visibility' not in data:
                scope_map = {'private': 'private', 'shared': 'workspace', 'global': 'public'}
                data['visibility'] = scope_map.get(data.pop('scope'), 'private')
        return data


class Commit(BaseModel):
    hash: str
    repo_id: str
    workspace_id: str
    agent_id: str
    author_id: str
    message: str
    parents: List[str] = Field(default_factory=list)
    tree_hash: Optional[str] = None
    memory_snapshot: List[str] = Field(default_factory=list)
    stats: Dict[str, int] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

    @model_validator(mode='before')
    @classmethod
    def check_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'author' in data and 'author_id' not in data:
                data['author_id'] = data['author']
            if 'author_id' not in data and 'agent_id' in data:
                data['author_id'] = data['agent_id']
        return data


class BranchRef(BaseModel):
    repo_id: str
    ref_name: str
    ref_type: RefType = RefType.BRANCH
    target_hash: str
    is_protected: bool = False
    updated_at: datetime = Field(default_factory=datetime.now)


class RefLogEntry(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    repo_id: str
    ref_name: str
    old_hash: Optional[str] = None
    new_hash: str
    action: str  # commit, checkout, merge, rollback, cherry-pick, reset
    actor_id: str
    message: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# LAYER 2 — Event Sourcing Models
# ============================================================

class GitMemEvent(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    event_type: EventType
    actor_id: str
    entity_type: str  # memory, commit, branch, repo, workspace
    entity_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# INFRA — Job Queue Models
# ============================================================

class Job(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    job_type: str  # embed, summarize, compact, gc, reindex
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


# ============================================================
# Agent Profile (kept for backward compat with agent_manager)
# ============================================================

class AgentProfile(BaseModel):
    id: str
    name: str
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    status: str = "offline"


# ============================================================
# Diff & Stats (used by VCS layer)
# ============================================================

class DiffStats(BaseModel):
    added: int
    modified: int
    deleted: int
    changes: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Quota Configuration
# ============================================================

PLAN_QUOTAS = {
    "free": {
        "max_repos": 3,
        "max_memories_per_repo": 1000,
        "max_vectors": 5000,
        "max_object_size_mb": 5,
        "max_monthly_embeddings": 10000,
    },
    "pro": {
        "max_repos": 25,
        "max_memories_per_repo": 50000,
        "max_vectors": 100000,
        "max_object_size_mb": 50,
        "max_monthly_embeddings": 500000,
    },
    "enterprise": {
        "max_repos": -1,
        "max_memories_per_repo": -1,
        "max_vectors": -1,
        "max_object_size_mb": 500,
        "max_monthly_embeddings": -1,
    },
}


# ============================================================
# Legacy Compat — RepositoryMetadata
# ============================================================

class RepositoryMetadata(BaseModel):
    name: str = "memory-store"
    description: str = "Central memory repository for AI agents"
    owner: str = "system"
    visibility: str = "public"
    created_at: datetime = Field(default_factory=datetime.now)
    star_count: int = 0
    fork_count: int = 0
    watcher_count: int = 0
    default_branch: str = "main"
    branches: Dict[str, str] = Field(default_factory=lambda: {"main": "HEAD"})
