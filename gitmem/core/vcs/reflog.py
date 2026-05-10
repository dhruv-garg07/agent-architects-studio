"""
GitMem v2.0 — RefLog (Audit Trail)

Immutable audit log of all reference changes (commits, checkouts, merges, rollbacks).
Used to recover lost commits and understand the repository history.
"""

from typing import Optional, List, Dict, Any
from gitmem.core.models import RefLogEntry


class RefLog:
    """Manages the reference log for a repository."""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self._table = "gitmem_reflog"

    def record(self, repo_id: str, ref_name: str, new_hash: str,
               action: str, actor_id: str, old_hash: Optional[str] = None,
               message: str = "") -> None:
        """Record a change to a reference."""
        if not self.client:
            return
            
        entry = RefLogEntry(
            repo_id=repo_id,
            ref_name=ref_name,
            old_hash=old_hash,
            new_hash=new_hash,
            action=action,
            actor_id=actor_id,
            message=message
        )
        
        try:
            self.client.table(self._table).insert(entry.model_dump(mode='json')).execute()
        except Exception as e:
            print(f"[RefLog] Failed to record entry: {e}")

    def get_history(self, repo_id: str, ref_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve the reflog history for a repository, optionally filtered by ref."""
        if not self.client:
            return []
            
        try:
            query = self.client.table(self._table).select("*").eq("repo_id", repo_id)
            if ref_name:
                query = query.eq("ref_name", ref_name)
                
            res = query.order("created_at", desc=True).limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[RefLog] Failed to get history: {e}")
            return []
