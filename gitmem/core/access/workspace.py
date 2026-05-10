"""
GitMem v2.0 — Workspace Manager

Manages Workspace entities, which are the root of the hierarchy.
Every Repo, Memory, User, and Agent belongs to a Workspace.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from gitmem.core.models import Workspace, WorkspaceMember, WorkspaceRole


class WorkspaceManager:
    """CRUD operations for Workspaces and Membership."""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self._table_workspace = "gitmem_workspaces"
        self._table_members = "gitmem_workspace_members"

    def create_workspace(self, name: str, slug: str, owner_id: str, plan: str = "free") -> Optional[Workspace]:
        """Create a new workspace and add the owner."""
        if not self.client:
            return None
            
        workspace = Workspace(name=name, slug=slug, owner_id=owner_id, plan=plan)
        
        try:
            # 1. Create Workspace
            self.client.table(self._table_workspace).insert(workspace.model_dump(mode='json')).execute()
            
            # 2. Add owner to members table
            member = WorkspaceMember(
                workspace_id=workspace.workspace_id,
                user_id=owner_id,
                role=WorkspaceRole.OWNER
            )
            self.client.table(self._table_members).insert(member.model_dump(mode='json')).execute()
            
            return workspace
        except Exception as e:
            print(f"[WorkspaceManager] Failed to create workspace: {e}")
            return None

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a workspace by ID."""
        if not self.client:
            return None
            
        try:
            res = self.client.table(self._table_workspace).select("*").eq("workspace_id", workspace_id).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"[WorkspaceManager] Failed to get workspace: {e}")
            return None

    def get_workspace_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Retrieve a workspace by URL slug."""
        if not self.client:
            return None
            
        try:
            res = self.client.table(self._table_workspace).select("*").eq("slug", slug).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"[WorkspaceManager] Failed to get workspace by slug: {e}")
            return None

    def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all workspaces a user belongs to."""
        if not self.client:
            return []
            
        try:
            # Requires a join or multiple queries
            member_res = self.client.table(self._table_members).select("workspace_id, role").eq("user_id", user_id).execute()
            if not member_res.data:
                return []
                
            workspace_ids = [m["workspace_id"] for m in member_res.data]
            ws_res = self.client.table(self._table_workspace).select("*").in_("workspace_id", workspace_ids).execute()
            
            # Combine roles
            workspaces = {w["workspace_id"]: w for w in ws_res.data}
            for m in member_res.data:
                if m["workspace_id"] in workspaces:
                    workspaces[m["workspace_id"]]["user_role"] = m["role"]
                    
            return list(workspaces.values())
        except Exception as e:
            print(f"[WorkspaceManager] Failed to list user workspaces: {e}")
            return []

    def add_member(self, workspace_id: str, user_id: str, role: WorkspaceRole, invited_by: str) -> bool:
        """Add a user to a workspace."""
        if not self.client:
            return False
            
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by
        )
        
        try:
            self.client.table(self._table_members).insert(member.model_dump(mode='json')).execute()
            return True
        except Exception as e:
            print(f"[WorkspaceManager] Failed to add member: {e}")
            return False

    def remove_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove a user from a workspace."""
        if not self.client:
            return False
            
        try:
            self.client.table(self._table_members).delete().eq("workspace_id", workspace_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            print(f"[WorkspaceManager] Failed to remove member: {e}")
            return False
            
    def get_members(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List all members of a workspace."""
        if not self.client:
            return []
            
        try:
            res = self.client.table(self._table_members).select("*").eq("workspace_id", workspace_id).execute()
            return res.data or []
        except Exception as e:
            print(f"[WorkspaceManager] Failed to get members: {e}")
            return []
