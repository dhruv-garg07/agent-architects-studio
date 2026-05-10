"""
GitMem v2.0 — RBAC Engine & Quotas

Enforces Role-Based Access Control policies and Plan Quotas.
Checks if an Actor is permitted to perform an Action on a Resource.
"""

from typing import Dict, Any, List
from gitmem.core.models import PLAN_QUOTAS, WorkspaceRole, RepoRole


class RBACEngine:
    """Enforces access control rules and resource quotas."""
    
    def __init__(self, workspace_manager, supabase_client):
        self.workspace_manager = workspace_manager
        self.client = supabase_client
        
        # Mapping of required roles for different actions
        self._action_role_map = {
            # Workspace Actions
            "workspace:delete": [WorkspaceRole.OWNER],
            "workspace:update_billing": [WorkspaceRole.OWNER, WorkspaceRole.ADMIN],
            "workspace:invite_member": [WorkspaceRole.OWNER, WorkspaceRole.ADMIN],
            "workspace:create_repo": [WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER],
            
            # Repo Actions (Require repo role or workspace admin)
            "repo:delete": [RepoRole.ADMIN, WorkspaceRole.OWNER],
            "repo:settings": [RepoRole.ADMIN, WorkspaceRole.OWNER, WorkspaceRole.ADMIN],
            "repo:commit": [RepoRole.WRITER, RepoRole.ADMIN, WorkspaceRole.OWNER, WorkspaceRole.ADMIN],
            "repo:read": [RepoRole.READER, RepoRole.WRITER, RepoRole.ADMIN, WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER]
        }

    def check_permission(self, actor_id: str, workspace_id: str, action: str, resource_id: str = None) -> bool:
        """
        Determine if the actor has permission to perform the action.
        """
        # 1. Get user's workspace role
        ws_role = self._get_workspace_role(workspace_id, actor_id)
        if not ws_role:
            return False
            
        allowed_roles = self._action_role_map.get(action, [])
        
        allowed_role_values = [r.value if hasattr(r, 'value') else r for r in allowed_roles]
        
        # If action is satisfied by workspace role alone
        if ws_role in allowed_role_values:
            return True
            
        # 2. Check repo-specific role if resource is a repo
        if resource_id and action.startswith("repo:"):
            repo_role = self._get_repo_role(resource_id, actor_id)
            if repo_role in allowed_role_values:
                return True
                
        return False

    def _get_workspace_role(self, workspace_id: str, user_id: str) -> str:
        """Get the user's role in the workspace."""
        if not self.client:
            return None
        try:
            res = self.client.table("gitmem_workspace_members") \
                .select("role").eq("workspace_id", workspace_id).eq("user_id", user_id).execute()
            if res.data:
                return res.data[0]["role"]
        except Exception:
            pass
        return None

    def _get_repo_role(self, repo_id: str, user_id: str) -> str:
        """Get the user's explicit role on a specific repository."""
        if not self.client:
            return None
        try:
            res = self.client.table("gitmem_collaborators") \
                .select("role").eq("repo_id", repo_id).eq("user_id", user_id).execute()
            if res.data:
                return res.data[0]["role"]
        except Exception:
            pass
        return None

    # ============================================================
    # Quota Enforcement
    # ============================================================

    def check_quota(self, workspace_id: str, resource_type: str, increment: int = 1) -> bool:
        """
        Check if an operation would exceed the workspace's quota.
        resource_type: "repos", "memories", "vectors", "monthly_embeddings"
        """
        workspace = self.workspace_manager.get_workspace(workspace_id)
        if not workspace:
            return False
            
        plan = workspace.get("plan", "free")
        quotas = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
        
        if resource_type == "repos":
            limit = quotas["max_repos"]
            if limit == -1: return True
            current = self._count_resource("gitmem_repos", "workspace_id", workspace_id)
            return (current + increment) <= limit
            
        elif resource_type == "memories":
            limit = quotas["max_memories_per_repo"]
            if limit == -1: return True
            current = self._count_resource("gitmem_memories", "workspace_id", workspace_id)
            # Roughly applying repo limit across workspace for stub
            return (current + increment) <= (limit * max(1, quotas["max_repos"]))
            
        return True

    def _count_resource(self, table: str, column: str, value: str) -> int:
        """Helper to count items in a table."""
        if not self.client: return 0
        try:
            res = self.client.table(table).select("*", count="exact").eq(column, value).limit(1).execute()
            return res.count or 0
        except Exception:
            return 0
