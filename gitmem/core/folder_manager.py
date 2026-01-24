"""
GitMem Folder Manager - Manages extended folder structure for agent data.

Provides unified access to:
- Context Store (episodic, semantic, procedural, working)
- Data Sources (api, mcp, webhooks, integrations)
- Documents (uploads, attachments, references)
- Checkpoints (snapshots, sessions, recovery)
- Activity Logs
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
from dataclasses import dataclass, field, asdict
from enum import Enum


class FolderType(Enum):
    """Types of folders in the GitMem structure."""
    # Context Store
    EPISODIC = "context/episodic"
    SEMANTIC = "context/semantic"
    PROCEDURAL = "context/procedural"
    WORKING = "context/working"
    
    # Data Sources
    API = "sources/api"
    MCP = "sources/mcp"
    WEBHOOKS = "sources/webhooks"
    INTEGRATIONS = "sources/integrations"
    
    # Documents
    UPLOADS = "documents/uploads"
    ATTACHMENTS = "documents/attachments"
    REFERENCES = "documents/references"
    
    # Checkpoints
    SNAPSHOTS = "checkpoints/snapshots"
    SESSIONS = "checkpoints/sessions"
    RECOVERY = "checkpoints/recovery"
    
    # Logs
    ACCESS_LOGS = "logs/access"
    MUTATION_LOGS = "logs/mutations"
    ERROR_LOGS = "logs/errors"


class AccessLevel(Enum):
    """Access control levels for folders."""
    READ = "read"
    WRITE = "write"
    APPEND = "append"
    DELETE = "delete"
    FULL = "full"
    NONE = "none"


@dataclass
class FolderPermissions:
    """Permissions for a folder."""
    user_read: bool = True
    user_write: bool = False
    user_delete: bool = False
    agent_read: bool = True
    agent_write: bool = True
    agent_delete: bool = False


# Define permissions for each folder type
FOLDER_PERMISSIONS = {
    # Context Store - Agent-managed
    FolderType.EPISODIC: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.SEMANTIC: FolderPermissions(user_read=True, user_write=True, agent_write=True),  # Append-only for users
    FolderType.PROCEDURAL: FolderPermissions(user_read=True, user_write=True, agent_write=True),
    FolderType.WORKING: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    
    # Data Sources - Mixed
    FolderType.API: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.MCP: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.WEBHOOKS: FolderPermissions(user_read=True, user_write=False, agent_write=False),
    FolderType.INTEGRATIONS: FolderPermissions(user_read=True, user_write=True, agent_write=False),
    
    # Documents - User-managed
    FolderType.UPLOADS: FolderPermissions(user_read=True, user_write=True, user_delete=True, agent_write=False),
    FolderType.ATTACHMENTS: FolderPermissions(user_read=True, user_write=True, user_delete=True, agent_write=False),
    FolderType.REFERENCES: FolderPermissions(user_read=True, user_write=True, user_delete=True, agent_write=False),
    
    # Checkpoints - Agent-managed
    FolderType.SNAPSHOTS: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.SESSIONS: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.RECOVERY: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    
    # Logs - System-managed
    FolderType.ACCESS_LOGS: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.MUTATION_LOGS: FolderPermissions(user_read=True, user_write=False, agent_write=True),
    FolderType.ERROR_LOGS: FolderPermissions(user_read=True, user_write=False, agent_write=True),
}


@dataclass
class Document:
    """Represents a document in the documents/ folder."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    folder: str = "uploads"  # uploads, attachments, references
    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    storage_path: str = ""
    content: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    uploaded_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Checkpoint:
    """Represents an agent checkpoint."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    checkpoint_type: str = "snapshot"  # snapshot, session, recovery, auto
    name: str = ""
    description: str = ""
    commit_hash: str = ""
    parent_checkpoint_id: Optional[str] = None
    memory_counts: Dict[str, int] = field(default_factory=dict)
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class APILog:
    """Represents an API call log entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    endpoint: str = ""
    method: str = "GET"
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Dict[str, Any] = field(default_factory=dict)
    response_status: int = 0
    response_data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    cached: bool = False
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MCPInput:
    """Represents an MCP server input/output."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    tool_name: str = ""
    tool_description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    success: bool = True
    error_message: str = ""
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Webhook:
    """Represents a received webhook event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    source: str = ""  # github, slack, custom
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    signature: str = ""
    processed: bool = False
    processed_at: Optional[str] = None
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ActivityLog:
    """Represents an activity log entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    log_type: str = "access"  # access, mutation, error, system
    action: str = ""  # read, write, delete, create
    resource_type: str = ""  # memory, document, checkpoint
    resource_id: str = ""
    actor_type: str = ""  # user, agent, system
    actor_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class FolderManager:
    """
    Manages the extended folder structure for GitMem.
    
    Provides CRUD operations for all folder types with proper
    access control and Supabase integration.
    """
    
    def __init__(self, supabase_client=None):
        """Initialize the folder manager."""
        self.db = supabase_client
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection if not provided."""
        if self.db is None:
            try:
                from .supabase_connector import SupabaseConnector
                connector = SupabaseConnector()
                self.db = connector.client
            except Exception as e:
                print(f"[FolderManager] Failed to connect to Supabase: {e}")
                self.db = None
    
    def check_permission(self, folder_type: FolderType, actor: str, action: str) -> bool:
        """Check if an actor has permission to perform an action on a folder."""
        perms = FOLDER_PERMISSIONS.get(folder_type)
        if not perms:
            return False
        
        if actor == "user":
            if action == "read":
                return perms.user_read
            elif action == "write":
                return perms.user_write
            elif action == "delete":
                return perms.user_delete
        elif actor == "agent":
            if action == "read":
                return perms.agent_read
            elif action == "write":
                return perms.agent_write
            elif action == "delete":
                return perms.agent_delete
        
        return False
    
    # =========================================================================
    # Document Operations
    # =========================================================================
    
    def add_document(self, doc: Document) -> str:
        """Add a document to the documents folder."""
        if not self.db:
            return doc.id
        
        try:
            data = asdict(doc)
            # Convert lists to proper format
            data['tags'] = doc.tags if doc.tags else []
            
            self.db.table("gitmem_documents").insert(data).execute()
            
            # Log activity
            self._log_activity(doc.agent_id, "mutation", "create", "document", doc.id, "user", doc.uploaded_by)
            
            return doc.id
        except Exception as e:
            print(f"[FolderManager] Error adding document: {e}")
            return doc.id
    
    def get_documents(self, agent_id: str, folder: str = None, limit: int = 50) -> List[Dict]:
        """Get documents for an agent."""
        if not self.db:
            return []
        
        try:
            query = self.db.table("gitmem_documents").select("*").eq("agent_id", agent_id)
            
            if folder:
                query = query.eq("folder", folder)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"[FolderManager] Error getting documents: {e}")
            return []
    
    def delete_document(self, agent_id: str, doc_id: str) -> bool:
        """Delete a document."""
        if not self.db:
            return False
        
        try:
            self.db.table("gitmem_documents").delete().eq("id", doc_id).eq("agent_id", agent_id).execute()
            self._log_activity(agent_id, "mutation", "delete", "document", doc_id, "user", "")
            return True
        except Exception as e:
            print(f"[FolderManager] Error deleting document: {e}")
            return False
    
    # =========================================================================
    # Checkpoint Operations
    # =========================================================================
    
    def create_checkpoint(self, checkpoint: Checkpoint) -> str:
        """Create a new checkpoint."""
        if not self.db:
            return checkpoint.id
        
        try:
            data = asdict(checkpoint)
            self.db.table("gitmem_checkpoints").insert(data).execute()
            
            self._log_activity(checkpoint.agent_id, "mutation", "create", "checkpoint", checkpoint.id, "agent", checkpoint.agent_id)
            
            return checkpoint.id
        except Exception as e:
            print(f"[FolderManager] Error creating checkpoint: {e}")
            return checkpoint.id
    
    def get_checkpoints(self, agent_id: str, checkpoint_type: str = None, limit: int = 20) -> List[Dict]:
        """Get checkpoints for an agent."""
        if not self.db:
            return []
        
        try:
            query = self.db.table("gitmem_checkpoints").select("*").eq("agent_id", agent_id)
            
            if checkpoint_type:
                query = query.eq("checkpoint_type", checkpoint_type)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"[FolderManager] Error getting checkpoints: {e}")
            return []
    
    def get_checkpoint_by_id(self, checkpoint_id: str) -> Optional[Dict]:
        """Get a specific checkpoint."""
        if not self.db:
            return None
        
        try:
            result = self.db.table("gitmem_checkpoints").select("*").eq("id", checkpoint_id).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"[FolderManager] Error getting checkpoint: {e}")
            return None
    
    # =========================================================================
    # API Log Operations
    # =========================================================================
    
    def log_api_call(self, log: APILog) -> str:
        """Log an API call."""
        if not self.db:
            return log.id
        
        try:
            data = asdict(log)
            self.db.table("gitmem_api_logs").insert(data).execute()
            return log.id
        except Exception as e:
            print(f"[FolderManager] Error logging API call: {e}")
            return log.id
    
    def get_api_logs(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Get API logs for an agent."""
        if not self.db:
            return []
        
        try:
            result = self.db.table("gitmem_api_logs").select("*").eq("agent_id", agent_id).order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"[FolderManager] Error getting API logs: {e}")
            return []
    
    # =========================================================================
    # MCP Input Operations
    # =========================================================================
    
    def log_mcp_input(self, mcp_input: MCPInput) -> str:
        """Log an MCP server input."""
        if not self.db:
            return mcp_input.id
        
        try:
            data = asdict(mcp_input)
            self.db.table("gitmem_mcp_inputs").insert(data).execute()
            return mcp_input.id
        except Exception as e:
            print(f"[FolderManager] Error logging MCP input: {e}")
            return mcp_input.id
    
    def get_mcp_inputs(self, agent_id: str, tool_name: str = None, limit: int = 50) -> List[Dict]:
        """Get MCP inputs for an agent."""
        if not self.db:
            return []
        
        try:
            query = self.db.table("gitmem_mcp_inputs").select("*").eq("agent_id", agent_id)
            
            if tool_name:
                query = query.eq("tool_name", tool_name)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"[FolderManager] Error getting MCP inputs: {e}")
            return []
    
    # =========================================================================
    # Webhook Operations
    # =========================================================================
    
    def log_webhook(self, webhook: Webhook) -> str:
        """Log a received webhook."""
        if not self.db:
            return webhook.id
        
        try:
            data = asdict(webhook)
            self.db.table("gitmem_webhooks").insert(data).execute()
            return webhook.id
        except Exception as e:
            print(f"[FolderManager] Error logging webhook: {e}")
            return webhook.id
    
    def get_webhooks(self, agent_id: str, source: str = None, processed: bool = None, limit: int = 50) -> List[Dict]:
        """Get webhooks for an agent."""
        if not self.db:
            return []
        
        try:
            query = self.db.table("gitmem_webhooks").select("*").eq("agent_id", agent_id)
            
            if source:
                query = query.eq("source", source)
            if processed is not None:
                query = query.eq("processed", processed)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"[FolderManager] Error getting webhooks: {e}")
            return []
    
    def mark_webhook_processed(self, webhook_id: str) -> bool:
        """Mark a webhook as processed."""
        if not self.db:
            return False
        
        try:
            self.db.table("gitmem_webhooks").update({
                "processed": True,
                "processed_at": datetime.now().isoformat()
            }).eq("id", webhook_id).execute()
            return True
        except Exception as e:
            print(f"[FolderManager] Error marking webhook processed: {e}")
            return False
    
    # =========================================================================
    # Activity Log Operations
    # =========================================================================
    
    def _log_activity(self, agent_id: str, log_type: str, action: str, 
                      resource_type: str, resource_id: str, actor_type: str, actor_id: str,
                      details: Dict = None):
        """Internal method to log activity."""
        if not self.db:
            return
        
        try:
            log = ActivityLog(
                agent_id=agent_id,
                log_type=log_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                actor_type=actor_type,
                actor_id=actor_id,
                details=details or {}
            )
            self.db.table("gitmem_activity_logs").insert(asdict(log)).execute()
        except Exception as e:
            print(f"[FolderManager] Error logging activity: {e}")
    
    def get_activity_logs(self, agent_id: str, log_type: str = None, limit: int = 100) -> List[Dict]:
        """Get activity logs for an agent."""
        if not self.db:
            return []
        
        try:
            query = self.db.table("gitmem_activity_logs").select("*").eq("agent_id", agent_id)
            
            if log_type:
                query = query.eq("log_type", log_type)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"[FolderManager] Error getting activity logs: {e}")
            return []
    
    # =========================================================================
    # Folder Statistics
    # =========================================================================
    
    def get_folder_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for all folders."""
        stats = {
            "context": {
                "episodic": 0,
                "semantic": 0,
                "procedural": 0,
                "working": 0
            },
            "sources": {
                "api": 0,
                "mcp": 0,
                "webhooks": 0,
                "integrations": 0
            },
            "documents": {
                "uploads": 0,
                "attachments": 0,
                "references": 0
            },
            "checkpoints": {
                "snapshots": 0,
                "sessions": 0,
                "recovery": 0
            }
        }
        
        if not self.db:
            return stats
        
        try:
            # Get memory counts by type
            for mem_type in ["episodic", "semantic", "procedural", "working"]:
                res = self.db.table("gitmem_memories").select("*", count="exact").eq("agent_id", agent_id).eq("type", mem_type).limit(1).execute()
                stats["context"][mem_type] = res.count or 0
            
            # Get document counts by folder
            for folder in ["uploads", "attachments", "references"]:
                res = self.db.table("gitmem_documents").select("*", count="exact").eq("agent_id", agent_id).eq("folder", folder).limit(1).execute()
                stats["documents"][folder] = res.count or 0
            
            # Get source counts
            stats["sources"]["api"] = len(self.get_api_logs(agent_id, limit=1000))
            stats["sources"]["mcp"] = len(self.get_mcp_inputs(agent_id, limit=1000))
            stats["sources"]["webhooks"] = len(self.get_webhooks(agent_id, limit=1000))
            
            # Get checkpoint counts
            for cp_type in ["snapshot", "session", "recovery"]:
                res = self.db.table("gitmem_checkpoints").select("*", count="exact").eq("agent_id", agent_id).eq("checkpoint_type", cp_type).limit(1).execute()
                stats["checkpoints"][cp_type.replace("snapshot", "snapshots").replace("session", "sessions")] = res.count or 0
                
        except Exception as e:
            print(f"[FolderManager] Error getting folder stats: {e}")
        
        return stats


# Singleton instance
_folder_manager = None

def get_folder_manager() -> FolderManager:
    """Get the singleton folder manager instance."""
    global _folder_manager
    if _folder_manager is None:
        _folder_manager = FolderManager()
    return _folder_manager
