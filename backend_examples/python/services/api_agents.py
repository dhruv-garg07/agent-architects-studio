import os
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from datetime import datetime
import uuid
"""
This is a file responsible for management of agents which is a table on the supabase.
This should also manage the Chroma DB memories as well. 
Each agent ID = Chroma DB collection name.
"""
class ApiAgentsService:
    """
    Service class for CRUD operations on the `api_agents` table.
    """

    # ---------- Table name ----------
    TABLE_NAME = "api_agents"

    # ---------- Required columns ----------
    REQUIRED_FIELDS = {
        "agent_name",
        "agent_slug",
        "permissions",
        "limits",
    }

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise RuntimeError("Supabase credentials not set in environment variables")

        self.client: Client = create_client(supabase_url, supabase_key)

    # =====================================================
    # CREATE
    # =====================================================
    def create_agent(
        self,
        user_id: str,
        agent_name: str,
        agent_slug: str,
        permissions: Dict[str, Any],
        limits: Dict[str, Any],
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Generate a unique agent_id
        agent_id = str(uuid.uuid4())
        payload = {
            "agent_id": agent_id,
            "user_id": user_id,
            "agent_name": agent_name,
            "agent_slug": agent_slug,
            "permissions": permissions,
            "limits": limits,
            "description": description,
            "metadata": metadata or {},
        }

        res = (
            self.client
            .table(self.TABLE_NAME)
            .insert(payload)
            .execute()
        )

        if not res.data:
            raise RuntimeError("Failed to create agent")

        return agent_id, res.data[0]

    # =====================================================
    # READ (by agent_id)
    # =====================================================
    def get_agent_by_id(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        query = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("agent_id", agent_id)
        )

        if user_id:
            query = query.eq("user_id", user_id)

        res = query.single().execute()
        return res.data

    # =====================================================
    # READ (list all agents for a user)
    # =====================================================
    def list_agents_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("user_id", user_id)
        )

        if status:
            query = query.eq("status", status)

        res = query.execute()
        return res.data or []

    # =====================================================
    # UPDATE
    # =====================================================
    def update_agent(
        self,
        agent_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not updates:
            raise ValueError("No update fields provided")

        updates["updated_at"] = datetime.utcnow().isoformat()

        res = (
            self.client
            .table(self.TABLE_NAME)
            .update(updates)
            .eq("agent_id", agent_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not res.data:
            raise RuntimeError("Update failed or agent not found")

        return res.data[0]

    # =====================================================
    # SOFT DELETE (recommended)
    # =====================================================
    def disable_agent(
        self,
        agent_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        return self.update_agent(
            agent_id=agent_id,
            user_id=user_id,
            updates={"status": "disabled"},
        )
        
    def enable_agent(
        self,
        agent_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        return self.update_agent(
            agent_id=agent_id,
            user_id=user_id,
            updates={"status": "active"},
        )

    # =====================================================
    # HARD DELETE (dangerous)
    # =====================================================
    def delete_agent(
        self,
        agent_id: str,
        user_id: str,
    ) -> bool:
        res = (
            self.client
            .table(self.TABLE_NAME)
            .delete()
            .eq("agent_id", agent_id)
            .eq("user_id", user_id)
            .execute()
        )

        return bool(res.data)
