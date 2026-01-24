from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, root_validator
import uuid

# --- Enums ---

class MemoryType(str, Enum):
    EPISODIC = "episodic"       # Events, logs, conversation history
    SEMANTIC = "semantic"       # Facts, knowledge, docs
    PROCEDURAL = "procedural"   # Skills, code, tool usage patterns
    WORKING = "working"         # Short-term, scratchpad
    STATE = "state"             # Internal variable snapshots

class MemoryScope(str, Enum):
    PRIVATE = "private"         # Agent-only
    SHARED = "shared"           # Team/Swarm accessible
    GLOBAL = "global"           # Public/Universal

# --- Base Models ---

class BaseMemory(BaseModel):
    """Immutable base memory unit."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    agent_id: str
    scope: MemoryScope = MemoryScope.PRIVATE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True

# --- Specific Memory Implementations ---

class EpisodicMemory(BaseMemory):
    """Trace of an event or thought."""
    content: str
    role: str = "assistant"     # user, system, assistant, tool
    context_id: Optional[str] = None  # thread_id or session_id
    importance: float = 0.5     # 0.0 to 1.0

class SemanticMemory(BaseMemory):
    """Fact or knowledge chunk."""
    content: str
    embedding: Optional[List[float]] = None
    keywords: List[str] = Field(default_factory=list)
    source_uri: Optional[str] = None # Where this fact came from

class ProceduralMemory(BaseMemory):
    """skill or tool capability."""
    name: str
    description: str
    code_snippet: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    success_rate: float = 0.0

class AgentState(BaseMemory):
    """Snapshot of agent execution state."""
    state_data: Dict[str, Any]
    step_number: int
    task_id: Optional[str] = None

# --- Versioning Models ---

class CommitInfo(BaseModel):
    hash: str
    message: str
    author: str
    timestamp: datetime
    stats: Dict[str, int] = Field(default_factory=dict)

class DiffInfo(BaseModel):
    added: int
    modified: int
    deleted: int
    changes: List[Dict[str, Any]]
