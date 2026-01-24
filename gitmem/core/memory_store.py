import os
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import MemoryItem, Commit, DiffStats, RepositoryMetadata as RepoMetadata
from .supabase_connector import SupabaseConnector
from .file_system import FileSystem

class MemoryStore:
    def __init__(self, root_path: str = "./gitmem_data"):
        self.root_path = root_path
        # self._ensure_dirs() # Disabled: Cloud only
        self._HEADS = {} 
        self.db = SupabaseConnector()
        self.fs = FileSystem(self)
        self.vector_engine = None # Injected by routes
        self._load_repo_metadata()

    def _ensure_dirs(self):
        # Deprecated: Cloud-only mode
        pass

    def _load_repo_metadata(self):
        # Load from DB, fallback to default in-memory
        data = self.db.get_repo_meta()
        if data:
            # Handle potential schema mismatch if DB has different fields
            try:
                self.repo_meta = RepoMetadata(**data)
            except:
                self.repo_meta = RepoMetadata()
        else:
            self.repo_meta = RepoMetadata()
            self._save_repo_metadata()

    def _save_repo_metadata(self):
        self.db.update_repo_meta(self.repo_meta.model_dump(mode='json'))

    def _get_head(self, agent_id: str) -> Optional[str]:
        # Ref path can be agent-specific or branch-specific. 
        # For MVP, agent_id maps to their "main" branch pointer or HEAD.
        if not agent_id:
            return None
            
        # Check in-memory cache of Repo Metadata
        return self.repo_meta.branches.get(agent_id) or self._HEADS.get(agent_id)

    def _set_head(self, agent_id: str, commit_hash: str):
        self._HEADS[agent_id] = commit_hash # Update in-memory
        
        # Persist as a branch/ref in Repo Metadata
        self.repo_meta.branches[agent_id] = commit_hash
        self._save_repo_metadata()
            
    def create_branch(self, branch_name: str, commit_hash: str) -> bool:
        """Create a new branch pointer."""
        if branch_name in self.repo_meta.branches:
            return False
            
        self.repo_meta.branches[branch_name] = commit_hash
        self._save_repo_metadata()
        return True
        
    def list_branches(self) -> Dict[str, str]:
        return self.repo_meta.branches

    def save_to_local_file(self, memory: MemoryItem):
        """Deprecated: Local file saving disabled."""
        pass

    def add_memory(self, memory: MemoryItem) -> str:
        # 1. Sync to Supabase (Cloud Persistence) ONLY
        self.db.add_memory(memory.model_dump(mode='json', exclude={'embedding'}))
        
        return memory.id

    def list_active_memory_ids(self, agent_id: str) -> List[str]:
        """
        Get all accessible memory IDs for an agent from Supabase (Cloud Only).
        """
        ids = []
        try:
            # Fetch from Supabase
            mems = self.db.get_memories(agent_id, None, limit=1000)
            if mems:
                ids = [m["id"] for m in mems]
        except Exception as e:
            print(f"Failed to fetch active memory IDs from cloud: {e}")
            
        return ids

    def commit_state(self, agent_id: str, message: str, author: str = "system") -> Commit:
        # 1. Identify Parent
        parent_hash = self._get_head(agent_id)
        parents = [parent_hash] if parent_hash else []
        
        # 2. Capture Snapshot (List of all current Memory IDs for this agent)
        snapshot_ids = self.list_active_memory_ids(agent_id)
        
        # 3. Create Commit Object
        # Hash is derived from content + parent + timestamp
        raw_content = f"{agent_id}{parents}{sorted(snapshot_ids)}{datetime.now().isoformat()}"
        commit_hash = hashlib.sha256(raw_content.encode()).hexdigest()[:16]
        
        commit = Commit(
            hash=commit_hash,
            message=message,
            agent_id=agent_id,
            author_id=author,
            parents=parents,
            memory_snapshot=snapshot_ids,
            timestamp=datetime.now()
        )
        
        # 4. Save Commit - CLOUD ONLY
        self.db.add_commit(commit.model_dump(mode='json'))
            
        # 5. Update HEAD
        self._set_head(agent_id, commit_hash)
        
        return commit

    def get_commit(self, commit_hash: str) -> Optional[Commit]:
        # Fetch from DB logic needed here if individual commit fetch is required
        # SupabaseConnector doesn't have `get_commit(hash)` yet, only `get_commits()`.
        # We can implement a filter in DB or fetch recent.
        # For now, simplistic scan of recent commits from DB.
        
        # Optimization: Add get_commit_by_hash to connector if needed.
        # Fallback to scanning get_commits output.
        commits = self.get_commits()
        for c in commits:
            if c.hash == commit_hash:
                return c
        return None

    def diff_commits(self, hash_a: str, hash_b: str) -> DiffStats:
        """
        Calculate delta between two commits (B - A).
        """
        commit_a = self.get_commit(hash_a)
        commit_b = self.get_commit(hash_b)
        
        if not commit_a or not commit_b:
            return DiffStats(added=0, modified=0, deleted=0, changes={"error": "Commit not found"})

        set_a = set(commit_a.memory_snapshot)
        set_b = set(commit_b.memory_snapshot)
        
        added = set_b - set_a
        deleted = set_a - set_b
        
        return DiffStats(
            added=len(added),
            modified=0,
            deleted=len(deleted),
            changes={
                "added_ids": list(added),
                "deleted_ids": list(deleted)
            }
        )
        
    def rollback(self, agent_id: str, target_hash: str) -> bool:
        """
        Hard reset HEAD to target_hash.
        """
        if not self.get_commit(target_hash):
            return False
            
        self._set_head(agent_id, target_hash)
        return True

    def fork(self, source_agent_id: str, target_agent_id: str) -> str:
        """
        Fork source agent's memory to target agent.
        """
        current_head = self._get_head(source_agent_id)
        if not current_head:
            raise ValueError("Source agent has no history")
            
        # Create ref for new agent pointing to same commit
        self._set_head(target_agent_id, current_head)
        return current_head

    # --- Read Ops ---
    
    def get_commits(self) -> List[Commit]:
        # Try DB only
        db_commits = self.db.get_commits(limit=50) # Increased limit slightly
        if db_commits:
            return [Commit(**c) for c in db_commits]
        return []

    def list_memories(self, agent_id: str, type: str, limit: int = 50) -> List[MemoryItem]:
        # Try DB only
        aid_query = agent_id if agent_id else None
        db_mems = self.db.get_memories(aid_query, type, limit)
        if db_mems:
            return [MemoryItem(**m) for m in db_mems]
        return []

    def list_known_agents(self) -> List[str]:
        """Get all known agent IDs from DB."""
        # 1. From DB
        db_agents = self.db.get_unique_agents()
        return list(db_agents)

    def count_memories(self, agent_id: str = None, mtype: str = None) -> int:
        """Count memories, optionally filtered."""
        # Try DB only
        return self.db.count_memories(agent_id, mtype)

    def get_folder_structure_stats(self, agent_id: str) -> Dict[str, Any]:
        """
        Get folder structure counts efficiently.
        """
        context_types = ["episodic", "semantic", "procedural", "short_term"]
        structure = {
            'context': {},
            'documents': {},
            'checkpoints': {},
            'checkpoints': {},
            'logs': {},
            'vectors': {}
        }
        total_memories = 0
        
        # 1. Context Bins
        for mtype in context_types:
            count = self.db.count_memories(agent_id, mtype)
            structure['context'][mtype] = {'count': count}
            total_memories += count
            
        # 2. Documents
        doc_count = self.db.count_memories(agent_id, "knowledge")
        structure['documents']['knowledge'] = {'count': doc_count}
        
        # 3. Checkpoints
        ckpt_count = self.db.count_checkpoints(agent_id, "stable")
        structure['checkpoints']['stable'] = {'count': ckpt_count}
        
        # 4. Logs
        log_count = self.db.count_logs(agent_id, "system")
        structure['logs']['system'] = {'count': log_count}
        
        # 5. Vectors
        if getattr(self, 'vector_engine', None):
            v_stats = self.vector_engine.get_agent_stats(agent_id)
            structure['vectors']['index'] = {'count': v_stats.get('embeddings', 0)}
            
        return {
            'total_memories': total_memories + doc_count,
            'structure': structure
        }

    def get_activity_feed(self, limit: int = 10) -> List[Dict]:
        """Get mixed activity feed (commits + memories)."""
        feed = []
        
        # 1. Get recent commits
        commits = self.get_commits()[:limit]
        for c in commits:
            feed.append({
                "type": "commit",
                "agent_id": c.agent_id,
                "content": f"Committed: {c.message}",
                "timestamp": c.timestamp, # datetime object
                "icon": "git-commit"
            })
            
        # 2. Get recent memories
        memories = self.list_memories("", "", limit=10) # Empty agent_id lists global recent?
        # Actually list_memories(agent_id, type) implementation:
        # self.db.get_memories(aid_query, type, limit)
        # If I pass "", "" -> get_memories(None, None, 10) which returns most recent global
        
        for m in memories:
            feed.append({
                "type": "memory",
                "agent_id": m.agent_id,
                "content": f"Added {m.type} memory: {m.content[:30]}...",
                "timestamp": m.created_at,
                "icon": "brain"
            })
            
        # Sort by timestamp desc
        feed.sort(key=lambda x: x['timestamp'], reverse=True)
        return feed[:limit]


