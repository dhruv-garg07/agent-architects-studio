"""
GitMem v2.0 — Branch Manager

Handles creation, deletion, protection, and listing of branches.
Uses the gitmem_refs table in Supabase.
"""

from typing import Optional, List, Dict, Any
from gitmem.core.models import BranchRef, RefType


class BranchManager:
    """Manages branches and tags in a repository."""
    
    def __init__(self, supabase_client, reflog=None):
        self.client = supabase_client
        self._table = "gitmem_refs"
        self.reflog = reflog

    def create_branch(self, repo_id: str, branch_name: str, target_hash: str, actor_id: str) -> bool:
        """Create a new branch pointing to a commit hash."""
        if not self.client:
            return False
            
        ref = BranchRef(
            repo_id=repo_id,
            ref_name=branch_name,
            ref_type=RefType.BRANCH,
            target_hash=target_hash
        )
        
        try:
            # Check if exists
            existing = self.get_branch(repo_id, branch_name)
            if existing:
                return False
                
            self.client.table(self._table).insert(ref.model_dump(mode='json')).execute()
            
            if self.reflog:
                self.reflog.record(
                    repo_id=repo_id,
                    ref_name=branch_name,
                    new_hash=target_hash,
                    action="branch created",
                    actor_id=actor_id
                )
            return True
        except Exception as e:
            print(f"[BranchManager] Failed to create branch: {e}")
            return False

    def update_branch(self, repo_id: str, branch_name: str, new_hash: str, actor_id: str, action: str = "commit") -> bool:
        """Update an existing branch to point to a new commit hash."""
        if not self.client:
            return False
            
        try:
            existing = self.get_branch(repo_id, branch_name)
            if not existing:
                return False
                
            if existing.get("is_protected") and action not in ["merge", "revert"]:
                # Protected branches may only be updated via merge or revert actions.
                print(f"[BranchManager] Branch '{branch_name}' is protected. "
                      f"Action '{action}' denied.")
                return False
                
            old_hash = existing.get("target_hash")
            
            self.client.table(self._table).update({"target_hash": new_hash}).eq("repo_id", repo_id).eq("ref_name", branch_name).execute()
            
            if self.reflog:
                self.reflog.record(
                    repo_id=repo_id,
                    ref_name=branch_name,
                    old_hash=old_hash,
                    new_hash=new_hash,
                    action=action,
                    actor_id=actor_id
                )
            return True
        except Exception as e:
            print(f"[BranchManager] Failed to update branch: {e}")
            return False

    def get_branch(self, repo_id: str, branch_name: str) -> Optional[Dict[str, Any]]:
        """Get a branch reference."""
        if not self.client:
            return None
            
        try:
            res = self.client.table(self._table).select("*").eq("repo_id", repo_id).eq("ref_name", branch_name).execute()
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            print(f"[BranchManager] Failed to get branch: {e}")
            return None

    def list_branches(self, repo_id: str) -> List[Dict[str, Any]]:
        """List all branches in a repository."""
        if not self.client:
            return []
            
        try:
            res = self.client.table(self._table).select("*").eq("repo_id", repo_id).eq("ref_type", RefType.BRANCH.value).execute()
            return res.data or []
        except Exception as e:
            print(f"[BranchManager] Failed to list branches: {e}")
            return []

    def delete_branch(self, repo_id: str, branch_name: str, actor_id: str) -> bool:
        """Delete a branch."""
        if not self.client:
            return False
            
        try:
            existing = self.get_branch(repo_id, branch_name)
            if not existing:
                return False
                
            if existing.get("is_protected"):
                print(f"[BranchManager] Cannot delete protected branch {branch_name}.")
                return False
                
            self.client.table(self._table).delete().eq("repo_id", repo_id).eq("ref_name", branch_name).execute()
            
            if self.reflog:
                self.reflog.record(
                    repo_id=repo_id,
                    ref_name=branch_name,
                    old_hash=existing.get("target_hash"),
                    new_hash="0000000000000000000000000000000000000000",
                    action="branch deleted",
                    actor_id=actor_id
                )
            return True
        except Exception as e:
            print(f"[BranchManager] Failed to delete branch: {e}")
            return False
