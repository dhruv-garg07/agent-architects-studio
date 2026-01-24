import os
import json
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env vars
load_dotenv()

class SupabaseConnector:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
        
        self.client: Optional[Client] = None
        self._disabled = False
        self._error_count = 0
        self._max_errors = 3
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                print(f"Supabase connected to {self.url}")
            except Exception as e:
                print(f"Failed to connect to Supabase: {e}")
                self._disabled = True
        else:
            # print("Supabase credentials not found in env.") 
            self._disabled = True

    def _handle_error(self, e):
        """Handle errors and trigger circuit breaker if needed."""
        if self._disabled:
            return
            
        self._error_count += 1
        msg = str(e)
        if "Could not find the table" in msg or "PGRST205" in msg:
            print(f"[Supabase] Table missing error (attempt {self._error_count}/{self._max_errors})")
        else:
            print(f"[Supabase] Error: {e}")
            
        if self._error_count >= self._max_errors:
            print("[Supabase] ⚠️ Too many errors. Disabling Supabase integration for this session.")
            print("[Supabase] Please run 'gitmem/schema.sql' in your Supabase SQL Editor to create tables.")
            self._disabled = True

    def add_memory(self, memory_data: Dict[str, Any]):
        if self._disabled or not self.client: return
        try:
            # Flatten metadata for jsonb if needed, Pydantic .dict() usually handles it
            # Ensure created_at is string
            data = memory_data.copy()
            if 'created_at' in data:
                data['created_at'] = str(data['created_at'])
                
            self.client.table("gitmem_memories").insert(data).execute()
            self._error_count = 0 # Reset on success
        except Exception as e:
            self._handle_error(e)

    def get_memories(self, agent_id: str = None, mtype: str = None, limit: int = 50) -> List[Dict]:
        if self._disabled or not self.client: return []
        try:
            query = self.client.table("gitmem_memories").select("*")
            if agent_id:
                query = query.eq("agent_id", agent_id)
            if mtype:
                query = query.eq("type", mtype)
            
            res = query.order("created_at", desc=True).limit(limit).execute()
            self._error_count = 0
            return res.data
        except Exception as e:
            self._handle_error(e)
            return []

    def count_memories(self, agent_id: str = None, mtype: str = None) -> int:
        if self._disabled or not self.client: return 0
        try:
            # count='exact' is supported by postgrest
            query = self.client.table("gitmem_memories").select("*", count="exact")
            if agent_id:
                query = query.eq("agent_id", agent_id)
            if mtype:
                query = query.eq("type", mtype)
            
            res = query.limit(1).execute()
            self._error_count = 0
            return res.count or 0
        except Exception as e:
            self._handle_error(e)
            return 0

    def add_commit(self, commit_data: Dict[str, Any]):
        if self._disabled or not self.client: return
        try:
            data = commit_data.copy()
            if 'timestamp' in data:
                data['timestamp'] = str(data['timestamp'])
            self.client.table("gitmem_commits").insert(data).execute()
            self._error_count = 0
        except Exception as e:
            self._handle_error(e)

    def get_commits(self, limit: int = 10) -> List[Dict]:
        if self._disabled or not self.client: return []
        try:
            res = self.client.table("gitmem_commits").select("*").order("timestamp", desc=True).limit(limit).execute()
            self._error_count = 0
            return res.data
        except Exception as e:
            self._handle_error(e)
            return []

    def update_repo_meta(self, meta_data: Dict[str, Any]):
        if self._disabled or not self.client: return
        try:
            # We assume single row id=1
            self.client.table("gitmem_repo_meta").upsert(meta_data).execute()
            self._error_count = 0
        except Exception as e:
            self._handle_error(e)

    def get_repo_meta(self) -> Dict[str, Any]:
        if self._disabled or not self.client: return {}
        try:
            res = self.client.table("gitmem_repo_meta").select("*").eq("id", 1).execute()
            self._error_count = 0
            if res.data:
                return res.data[0]
            return {}
        except Exception as e:
            self._handle_error(e)
        return {}

    def get_unique_agents(self) -> List[str]:
        """Fetch list of unique agent IDs from memories."""
        if self._disabled or not self.client: return []
        try:
            res = self.client.table("gitmem_memories").select("agent_id").limit(1000).execute()
            if res.data:
                unique = set(row['agent_id'] for row in res.data if row.get('agent_id'))
                return list(unique)
            return []
        except Exception as e:
            self._handle_error(e)
            return []

    # --- Checkpoints ---

    def add_checkpoint(self, data: Dict[str, Any]):
        if self._disabled or not self.client: return
        try:
            # Map 'type' to 'checkpoint_type' if passed by legacy/generic callers
            if 'type' in data and 'checkpoint_type' not in data:
                data['checkpoint_type'] = data.pop('type')
            
            if 'created_at' in data: data['created_at'] = str(data['created_at'])
            self.client.table("gitmem_checkpoints").insert(data).execute()
            self._error_count = 0
        except Exception as e:
            self._handle_error(e)

    def get_checkpoints(self, agent_id: str, type: str = None, limit: int = 50) -> List[Dict]:
        if self._disabled or not self.client: return []
        try:
            query = self.client.table("gitmem_checkpoints").select("*").eq("agent_id", agent_id)
            if type: query = query.eq("checkpoint_type", type)
            return query.order("created_at", desc=True).limit(limit).execute().data
        except Exception as e:
            self._handle_error(e)
            return []

    def count_checkpoints(self, agent_id: str, type: str = None) -> int:
        if self._disabled or not self.client: return 0
        try:
            query = self.client.table("gitmem_checkpoints").select("*", count="exact").eq("agent_id", agent_id)
            if type: query = query.eq("checkpoint_type", type)
            return query.limit(1).execute().count
        except Exception as e:
            self._handle_error(e)
            return 0

    # --- Logs ---

    def add_log(self, data: Dict[str, Any]):
        if self._disabled or not self.client: return
        try:
            # The logs table uses 'type' as confirmed by screenshot.
            if 'log_type' in data and 'type' not in data:
                data['type'] = data.pop('log_type')
                
            if 'created_at' in data: data['created_at'] = str(data['created_at'])
            self.client.table("gitmem_logs").insert(data).execute()
            self._error_count = 0
        except Exception as e:
            self._handle_error(e)

    def get_logs(self, agent_id: str, type: str = None, limit: int = 50) -> List[Dict]:
        if self._disabled or not self.client: return []
        try:
            query = self.client.table("gitmem_logs").select("*").eq("agent_id", agent_id)
            if type: query = query.eq("type", type)
            return query.order("created_at", desc=True).limit(limit).execute().data
        except Exception as e:
            self._handle_error(e)
            return []

    def count_logs(self, agent_id: str, type: str = None) -> int:
        if self._disabled or not self.client: return 0
        try:
            query = self.client.table("gitmem_logs").select("*", count="exact").eq("agent_id", agent_id)
            if type: query = query.eq("type", type)
            return query.limit(1).execute().count
        except Exception as e:
            self._handle_error(e)
            return 0

