"""
GitMem v2.0 — Collaborator Manager

Manages repository-level collaborations. Allows sharing specific
repositories with users who aren't necessarily full workspace members.
"""

from typing import Dict, Any, List
from gitmem.core.models import Collaborator, RepoRole


class CollabManager:
    """Manages repository collaborators."""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self._table = "gitmem_collaborators"

    def add_collaborator(self, repo_id: str, user_id: str, role: RepoRole, added_by: str) -> bool:
        """Add a collaborator to a repository."""
        if not self.client:
            return False
            
        collab = Collaborator(
            repo_id=repo_id,
            user_id=user_id,
            role=role,
            added_by=added_by
        )
        
        try:
            self.client.table(self._table).insert(collab.model_dump(mode='json')).execute()
            return True
        except Exception as e:
            print(f"[CollabManager] Failed to add collaborator: {e}")
            return False

    def remove_collaborator(self, repo_id: str, user_id: str) -> bool:
        """Remove a collaborator from a repository."""
        if not self.client:
            return False
            
        try:
            self.client.table(self._table).delete().eq("repo_id", repo_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"[CollabManager] Failed to remove collaborator: {e}")
            return False

    def get_collaborators(self, repo_id: str) -> List[Dict[str, Any]]:
        """List all collaborators for a repository."""
        if not self.client:
            return []
            
        try:
            res = self.client.table(self._table).select("*").eq("repo_id", repo_id).execute()
            return res.data or []
        except Exception as e:
            print(f"[CollabManager] Failed to list collaborators: {e}")
            return []

    def update_role(self, repo_id: str, user_id: str, new_role: RepoRole) -> bool:
        """Update a collaborator's role."""
        if not self.client:
            return False
            
        try:
            self.client.table(self._table).update({"role": new_role.value}).eq("repo_id", repo_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"[CollabManager] Failed to update role: {e}")
            return False
