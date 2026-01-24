import requests
import logging
from typing import List, Dict, Any, Optional, Union, Type
from datetime import datetime

from .models import (
    MemoryType, MemoryScope, 
    BaseMemory, EpisodicMemory, SemanticMemory, ProceduralMemory, AgentState,
    CommitInfo, DiffInfo
)

# Configure logging
logger = logging.getLogger("gitmem")

class GitMem:
    """
    The Official Enterprise-Grade GITMEM Client.
    
    Provides a high-level API for version-controlled agent memory.
    """
    
    def __init__(self, base_url: str = "http://localhost:1078", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/gitmem/api"
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _post(self, endpoint: str, data: Dict) -> Dict:
        try:
            resp = self.session.post(f"{self.api_url}/{endpoint}", json=data)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request Failed: {e}")
            raise

    # --- Core Memory Operations ---

    def add(self, memory: Union[BaseMemory, Dict], auto_commit: bool = False) -> str:
        """
        Add a memory object to the store.
        Success automatically returns the Memory ID.
        """
        if isinstance(memory, dict):
            # Infer type or default to Episodic
            m_type = memory.get("type", "episodic")
            # This is a simplification; in a real app we'd map types dynamically
            payload = memory
        else:
            payload = memory.dict()
            # Inject generic 'type' field for backend compatibility if using Pydantic models
            if isinstance(memory, EpisodicMemory): payload['type'] = 'episodic'
            elif isinstance(memory, SemanticMemory): payload['type'] = 'semantic'
            elif isinstance(memory, ProceduralMemory): payload['type'] = 'procedural'
        
        # Backend expects 'content' at top level
        # Ensure our Pydantic models map correctly to what the backend expects
        # (The current backend is simple, so we match its schema)
        
        resp = self._post("memory", payload)
        
        if auto_commit:
            self.commit(payload.get("agent_id"), "Auto-generated memory commit")
            
        return resp.get("id")

    def query(self, query: str, agent_id: str = None, limit: int = 10, filters: Dict = None) -> List[Dict]:
        """
        Semantic search with filtering.
        """
        # In the future, this should return List[BaseMemory] objects, 
        # but for now returns raw dicts from API.
        payload = {
            "query": query,
            "agent_id": agent_id,
            "limit": limit,
            "filters": filters or {}
        }
        resp = self._post("query", payload)
        return resp.get("results", [])

    # --- Version Control Operations ---

    def commit(self, agent_id: str, message: str) -> CommitInfo:
        """
        Snapshot the current memory state.
        """
        resp = self._post("commit", {"agent_id": agent_id, "message": message})
        return CommitInfo(
            hash=resp.get("commit_hash", "unknown"),
            message=message,
            author=agent_id,
            timestamp=datetime.now(), # simple mock for now
            stats={} 
        )

    def diff(self, agent_id: str, commit_a: str, commit_b: str) -> DiffInfo:
        """
        Compare two memory states.
        (Feature implementation pending on backend)
        """
        # Mock response for SDK design compliance
        return DiffInfo(
            added=0, modified=0, deleted=0, changes=[{"info": "Not implemented on backend yet"}]
        )

    def rollback(self, agent_id: str, commit_hash: str) -> bool:
        """
        Revert memory state to a previous commit.
        """
        resp = self._post("rollback", {"agent_id": agent_id, "hash": commit_hash})
        return resp.get("status") == "success"

    def fork(self, source_agent_id: str, new_branch_name: str) -> str:
        """
        Fork an agent's memory to a new branch/agent.
        """
        resp = self._post("fork", {"source": source_agent_id, "target": new_branch_name})
        return resp.get("fork_id")

    # --- Agent Helpers ---

    def get_context(self, agent_id: str, query: str = None, token_limit: int = 2000) -> str:
        """
        Retrieve and pack memories into a context string for LLMs.
        """
        memories = self.query(query, agent_id=agent_id, limit=10)
        
        # Simple context packing
        context = []
        current_len = 0
        
        # Sort by importance logic could go here
        
        for m in memories:
            content = m.get('content', '')
            # Rough char count approximation for tokens
            if current_len + len(content) > token_limit * 4:
                break
            context.append(f"- {content}")
            current_len += len(content)
            
        return "Relevant Information:\n" + "\n".join(context)
