from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, model_validator
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    STATE = "state"

class MemoryScope(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    GLOBAL = "global"

class MemoryItem(BaseModel):
    id: str = Field(default_factory=generate_uuid)
    agent_id: str
    type: MemoryType = MemoryType.EPISODIC
    content: str
    
    # Enhanced Metadata
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    importance: float = 0.0
    tags: List[str] = Field(default_factory=list)
    scope: MemoryScope = MemoryScope.PRIVATE
    provenance: Optional[str] = None # Author signature or source hash
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Versioning linkage
    commit_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/indexing."""
        res = self.model_dump(mode='json', exclude={'metadata'})
        # Merge internal metadata field
        if self.metadata:
            res.update(self.metadata)
        # Ensure critical identification fields are present in flattened metadata
        res['agent_id'] = self.agent_id
        res['type'] = self.type.value if hasattr(self.type, 'value') else str(self.type)
        return res

class AgentProfile(BaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    llm_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    status: str = "offline" # online, offline, busy

class Commit(BaseModel):
    hash: str
    message: str
    agent_id: str # Repo ID / Owner
    author_id: str # Committer
    parents: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # State Snapshot
    tree_hash: Optional[str] = None # Merkle root of the snapshot
    memory_snapshot: List[str] = Field(default_factory=list) # List of MemoryItem IDs
    
    stats: Dict[str, int] = Field(default_factory=dict) # added, deleted, modified count

    @model_validator(mode='before')
    @classmethod
    def check_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map 'author' (old) to 'author_id' (new)
            if 'author' in data and 'author_id' not in data:
                data['author_id'] = data['author']
            # Fallback if neither exists but agent_id does 
            if 'author_id' not in data and 'agent_id' in data:
                 data['author_id'] = data['agent_id'] # Assume agent authored their own commit
        return data

class RepositoryMetadata(BaseModel):
    name: str = "memory-store"
    description: str = "Central memory repository for AI agents"
    owner: str = "system"
    visibility: str = "public"
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Stats
    star_count: int = 0
    fork_count: int = 0
    watcher_count: int = 0
    
    # Branching
    default_branch: str = "main"
    branches: Dict[str, str] = Field(default_factory=lambda: {"main": "HEAD"})

class DiffStats(BaseModel):
    added: int
    modified: int
    deleted: int
    changes: Dict[str, Any]
