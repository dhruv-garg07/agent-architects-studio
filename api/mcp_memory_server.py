"""
MCP Server for Manhattan Memory CRUD APIs

This MCP (Model Context Protocol) server exposes the Memory CRUD functionality
to Claude and other MCP-compatible clients. It provides tools for:
- Creating memory systems for agents
- Processing raw dialogues through LLM
- Adding memories directly (without LLM)
- Reading/searching memories using hybrid retrieval
- Getting context-aware answers
- Updating existing memories
- Deleting memories

Usage:
    Run with: python mcp_memory_server.py
    Or with uv: uv run mcp_memory_server.py

Configuration for Claude Desktop (claude_desktop_config.json):
{
    "mcpServers": {
        "manhattan-memory": {
            "command": "python",
            "args": ["<ABSOLUTE_PATH>/mcp_memory_server.py"]
        }
    }
}
"""

import os
import sys
import json
from typing import Any, Optional, List, Dict

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Add lib directory
lib_dir = os.path.join(parent_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not installed. Install with: pip install mcp")
    print("Or: uv add mcp")
    sys.exit(1)

# Import GitMem V2 Core
try:
    from gitmem.core.app import gitmem_app
except ImportError as e:
    print(f"Error importing GitMem V2: {e}")
    sys.exit(1)

# Initialize FastMCP server
mcp = FastMCP(
    "manhattan-memory",
    instructions="""
You have access to a PERSISTENT MEMORY SYSTEM for storing and retrieving information.
This allows you to provide a more personalized and consistent experience.

PROACTIVE MEMORY USAGE:
1.  **SAVE IMPORTANT INFO**: If the user shares facts, preferences, or project details, store them.
2.  **CHECK CONTEXT**: Before answering context-heavy questions, check if you already know the answer.

This system is designed to HELP you, not to block you. Use it when it improves your response quality.

⚙️ CONFIGURATION:
-   `agent_id`: Optional. defaults to the enterprise agent (ID: `84aab1f8-3ea9-4c6a-aa3c-cd8eaa274a5e`) if not specified.
"""
)

# Workspace context for this session
_current_workspace_id: Optional[str] = os.getenv("DEFAULT_WORKSPACE_ID", "default_workspace")

# Current agent context for this session
_current_agent_id: Optional[str] = None


# ============================================================================
# MCP Agents Service - CRUD for managing agent_ids in Supabase
# ============================================================================

class McpAgentsService:
    """
    Service class for CRUD operations on the `mcp_agents` table.
    Each agent represents a memory context that users can switch between.
    """
    
    TABLE_NAME = "mcp_agents"
    
    def __init__(self):
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            self.client = None
            print("Warning: Supabase credentials not set. Agent management will work locally only.")
        else:
            self.client = create_client(supabase_url, supabase_key)
    
    def create_agent(
        self,
        user_id: str,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new MCP agent."""
        import uuid
        from datetime import datetime
        
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "agent_id": agent_id,
            "name": name or agent_id,
            "description": description or "",
            "metadata": json.dumps(metadata) if metadata else "{}",
            "status": "active",
            "is_current": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if self.client:
            # Check if agent_id already exists for this user
            existing = self.client.table(self.TABLE_NAME).select("id").eq("user_id", user_id).eq("agent_id", agent_id).execute()
            if existing.data:
                raise ValueError(f"Agent '{agent_id}' already exists for this user")
            
            res = self.client.table(self.TABLE_NAME).insert(record).execute()
            if res.data:
                return res.data[0]
        
        return record  # Fallback for local testing
    
    def get_agent(self, user_id: str, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific agent by agent_id."""
        if self.client:
            res = self.client.table(self.TABLE_NAME).select("*").eq("user_id", user_id).eq("agent_id", agent_id).limit(1).execute()
            if res.data:
                agent = res.data[0]
                if agent.get("metadata") and isinstance(agent["metadata"], str):
                    try:
                        agent["metadata"] = json.loads(agent["metadata"])
                    except:
                        pass
                return agent
        return None
    
    def list_agents(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all agents for a user."""
        if self.client:
            query = self.client.table(self.TABLE_NAME).select("*").eq("user_id", user_id)
            if status:
                query = query.eq("status", status)
            res = query.order("created_at", desc=True).execute()
            agents = res.data or []
            for agent in agents:
                if agent.get("metadata") and isinstance(agent["metadata"], str):
                    try:
                        agent["metadata"] = json.loads(agent["metadata"])
                    except:
                        pass
            return agents
        return []
    
    def update_agent(self, user_id: str, agent_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an agent."""
        from datetime import datetime
        
        if not updates:
            raise ValueError("No updates provided")
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            updates["metadata"] = json.dumps(updates["metadata"])
        
        if self.client:
            res = self.client.table(self.TABLE_NAME).update(updates).eq("user_id", user_id).eq("agent_id", agent_id).execute()
            if res.data:
                agent = res.data[0]
                if agent.get("metadata") and isinstance(agent["metadata"], str):
                    try:
                        agent["metadata"] = json.loads(agent["metadata"])
                    except:
                        pass
                return agent
        return None
    
    def delete_agent(self, user_id: str, agent_id: str) -> bool:
        """Delete an agent."""
        if self.client:
            res = self.client.table(self.TABLE_NAME).delete().eq("user_id", user_id).eq("agent_id", agent_id).execute()
            return bool(res.data)
        return False
    
    def set_current_agent(self, user_id: str, agent_id: str) -> bool:
        """Set an agent as the current/default for the user."""
        from datetime import datetime
        
        if self.client:
            # Clear is_current from all agents
            self.client.table(self.TABLE_NAME).update({"is_current": False}).eq("user_id", user_id).execute()
            # Set is_current for this agent
            res = self.client.table(self.TABLE_NAME).update({
                "is_current": True, 
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).eq("agent_id", agent_id).execute()
            return bool(res.data)
        return False
    
    def get_current_agent(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the current/default agent for the user."""
        if self.client:
            # Try to get current agent
            res = self.client.table(self.TABLE_NAME).select("*").eq("user_id", user_id).eq("is_current", True).limit(1).execute()
            if res.data:
                agent = res.data[0]
            else:
                # Fallback to most recent
                res = self.client.table(self.TABLE_NAME).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
                if res.data:
                    agent = res.data[0]
                else:
                    return None
            
            if agent.get("metadata") and isinstance(agent["metadata"], str):
                try:
                    agent["metadata"] = json.loads(agent["metadata"])
                except:
                    pass
            return agent
        return None


# Initialize the agents service
_agents_service = McpAgentsService()

# Default user_id for MCP (can be overridden by environment variable)
_default_user_id = os.getenv("MCP_USER_ID", "mcp-default-user")


# Removed SimpleMem cache helper


# ============================================================================
# MCP TOOLS - Agent Management (CRUD for mcp_agents)
# ============================================================================

@mcp.tool()
async def register_agent(
    agent_id: str,
    name: str = None,
    description: str = ""
) -> str:
    """
    Register a new memory agent in the system.
    
    Each agent has its own separate memory space. Use different agents
    for different projects, contexts, or purposes.
    
    Args:
        agent_id: Unique identifier (e.g., 'project-notes', 'daily-journal')
                  Must contain only letters, numbers, hyphens, and underscores.
        name: Human-readable name (optional, defaults to agent_id)
        description: Description of the agent's purpose (optional)
    
    Returns:
        JSON string with the created agent details
    """
    global _current_agent_id
    
    try:
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
            return json.dumps({
                'ok': False, 
                'error': 'agent_id must contain only alphanumeric characters, hyphens, and underscores'
            })
        
        agent = _agents_service.create_agent(
            user_id=_default_user_id,
            agent_id=agent_id,
            name=name or agent_id,
            description=description
        )
        
        # Set as current agent
        _current_agent_id = agent_id
        _agents_service.set_current_agent(_default_user_id, agent_id)
        
        # Also initialize the workspace/repo in GitMem V2 if needed
        # We assume the agent_id corresponds to a repo_id in GitMem V2
        # Future improvement: map these explicitly.
        
        return json.dumps({
            'ok': True,
            'message': 'agent_registered',
            'agent': agent,
            'current_agent': agent_id
        })
    except ValueError as e:
        return json.dumps({'ok': False, 'error': str(e)})
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def list_my_agents() -> str:
    """
    List all your registered memory agents.
    
    Shows all agents you've created with their names, descriptions,
    and status. Use this to see what memory contexts are available.
    
    Returns:
        JSON string with list of all your agents
    """
    try:
        agents = _agents_service.list_agents(user_id=_default_user_id)
        return json.dumps({
            'ok': True,
            'agents': agents,
            'count': len(agents),
            'current_agent': _current_agent_id
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def get_agent_details(agent_id: str) -> str:
    """
    Get details about a specific memory agent.
    
    Args:
        agent_id: The agent identifier to look up
    
    Returns:
        JSON string with agent details (name, description, metadata, etc.)
    """
    try:
        agent = _agents_service.get_agent(user_id=_default_user_id, agent_id=agent_id)
        if agent:
            return json.dumps({'ok': True, 'agent': agent})
        return json.dumps({'ok': False, 'error': 'agent_not_found'})
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def update_agent_info(
    agent_id: str,
    name: str = None,
    description: str = None
) -> str:
    """
    Update a memory agent's details.
    
    Args:
        agent_id: The agent to update
        name: New name (optional)
        description: New description (optional)
    
    Returns:
        JSON string with updated agent details
    """
    try:
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        
        if not updates:
            return json.dumps({'ok': False, 'error': 'No updates provided'})
        
        agent = _agents_service.update_agent(
            user_id=_default_user_id,
            agent_id=agent_id,
            updates=updates
        )
        
        if agent:
            return json.dumps({'ok': True, 'agent': agent})
        return json.dumps({'ok': False, 'error': 'agent_not_found'})
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def remove_agent(agent_id: str, delete_memories: bool = False) -> str:
    """
    Remove a memory agent from the system.
    
    WARNING: This permanently removes the agent. Set delete_memories=True
    to also delete all memories associated with this agent.
    
    Args:
        agent_id: The agent to delete
        delete_memories: Also delete all memories in this agent (default: False)
    
    Returns:
        JSON string with deletion status
    """
    global _current_agent_id
    
    try:
        # 1. Delete the agent record from mcp_agents table
        deleted = _agents_service.delete_agent(user_id=_default_user_id, agent_id=agent_id)

        memories_deleted_count = 0

        # 2. Optionally delete all memories from GitMem V2 (Supabase + ChromaDB)
        if delete_memories:
            db = gitmem_app.supabase_client
            if db:
                try:
                    # Delete all gitmem_memories rows for this agent (repo_id = agent_id)
                    del_res = (
                        db.table("gitmem_memories")
                        .delete()
                        .eq("repo_id", agent_id)
                        .execute()
                    )
                    memories_deleted_count = len(del_res.data) if del_res.data else 0
                except Exception as mem_err:
                    print(f"[MCP] Warning: Could not delete memories for {agent_id}: {mem_err}")

            # Also drop the ChromaDB collection for this agent (best-effort)
            if gitmem_app.vector_engine and gitmem_app.vector_engine.client:
                try:
                    gitmem_app.vector_engine.client.delete_collection(agent_id)
                except Exception as vec_err:
                    print(f"[MCP] Warning: Could not drop ChromaDB collection {agent_id}: {vec_err}")

        # 3. Clear session context if this was the active agent
        global _current_agent_id
        if _current_agent_id == agent_id:
            _current_agent_id = None

        return json.dumps({
            "ok": True,
            "message": "agent_removed",
            "agent_id": agent_id,
            "memories_deleted": delete_memories,
            "memories_deleted_count": memories_deleted_count,
            "current_agent": _current_agent_id
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
async def switch_to_agent(agent_id: str) -> str:
    """
    Switch to a different memory agent context.
    
    After switching, subsequent memory operations will use this agent
    by default when agent_id is not explicitly specified.
    
    Args:
        agent_id: The agent to switch to
    
    Returns:
        JSON string confirming the switch
    """
    global _current_agent_id
    
    try:
        # Verify agent exists
        agent = _agents_service.get_agent(user_id=_default_user_id, agent_id=agent_id)
        
        if agent:
            _current_agent_id = agent_id
            _agents_service.set_current_agent(_default_user_id, agent_id)
            
            # (No local memory cache init needed for V2)
            
            return json.dumps({
                'ok': True,
                'message': f'Switched to agent: {agent_id}',
                'current_agent': agent_id,
                'agent': agent
            })
        else:
            return json.dumps({
                'ok': False,
                'error': f"Agent '{agent_id}' not found. Create it first with register_agent()",
                'current_agent': _current_agent_id
            })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def current_agent() -> str:
    """
    Get the current/active memory agent context.
    
    Returns the agent that is currently being used for memory operations.
    
    Returns:
        JSON string with current agent details
    """
    global _current_agent_id
    
    try:
        if _current_agent_id:
            agent = _agents_service.get_agent(user_id=_default_user_id, agent_id=_current_agent_id)
            return json.dumps({
                'ok': True,
                'current_agent': _current_agent_id,
                'agent': agent
            })
        
        # Try to get from server
        agent = _agents_service.get_current_agent(user_id=_default_user_id)
        if agent:
            _current_agent_id = agent.get('agent_id')
            return json.dumps({
                'ok': True,
                'current_agent': _current_agent_id,
                'agent': agent
            })
        
        return json.dumps({
            'ok': True,
            'current_agent': None,
            'message': 'No current agent set. Use switch_to_agent() or register_agent() first.'
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


# ============================================================================
# MCP TOOLS - Memory CRUD Operations
# ============================================================================

@mcp.tool()
async def create_memory(agent_id: str, clear_db: bool = False) -> str:
    """
    Create/initialize a SimpleMem memory system for an agent.
    
    This creates a ChromaDB collection for storing memory entries.
    Set clear_db to True to clear existing memories.
    
    Args:
        agent_id: Unique identifier for the agent
        clear_db: Whether to clear existing memories (default: False)
    
    Returns:
        JSON string with creation status
    """
    try:
        # In GitMem V2, repositories/agents are created dynamically or exist in DB.
        # We don't need to explicitly create a local SimpleMem system anymore.
        return json.dumps({
            'ok': True,
            'message': 'memory_system_created' if clear_db else 'memory_system_initialized',
            'agent_id': agent_id,
            'cleared': clear_db
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def process_raw_dialogues(
    agent_id: str,
    dialogues: List[Dict[str, str]]
) -> str:
    """
    Process raw dialogues through LLM to extract structured memory entries.
    
    Flow: ADD_DIALOGUE → LLM → JSON RESPONSE → N Memory units → Vector Store.
    Each dialogue is processed to extract facts, entities, timestamps, and keywords.
    
    Args:
        agent_id: Unique identifier for the agent
        dialogues: List of dialogue objects, each with keys:
                   - speaker: Name of the speaker
                   - content: The dialogue content
                   - timestamp: (optional) ISO8601 timestamp
    
    Returns:
        JSON string with processing status and count of dialogues processed
    """
    try:
        if not dialogues:
            return json.dumps({'ok': False, 'error': 'dialogues list is required'})
        
        res = gitmem_app.command_handler.execute(
            command_name="add_memory",
            actor_id=_default_user_id,
            workspace_id=_current_workspace_id,
            payload={
                "repo_id": agent_id,
                "text": "\n".join([f"{d.get('speaker', 'unknown')}: {d.get('content', '')}" for d in dialogues]),
                "metadata": {"source": "dialogue_tool"}
            },
            skip_auth=True
        )
        memories_created = res.get("data", {}).get("memories_added", 0) if res.get("status") == "success" else 0
        
        return json.dumps({
            'ok': True,
            'message': 'dialogues_processed',
            'agent_id': agent_id,
            'dialogues_processed': memories_created
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def add_memory_direct(
    agent_id: str,
    memories: List[Dict[str, Any]]
) -> str:
    """
    Directly save pre-structured memory entries without LLM processing.
    
    Use this when you already have structured memory data and want to bypass
    the LLM extraction step.
    
    Args:
        agent_id: Unique identifier for the agent
        memories: List of memory objects, each with keys:
                  - lossless_restatement: (required) Self-contained fact statement
                  - keywords: (optional) List of keywords
                  - timestamp: (optional) ISO8601 timestamp
                  - location: (optional) Location string
                  - persons: (optional) List of person names
                  - entities: (optional) List of entities
                  - topic: (optional) Topic phrase
    
    Returns:
        JSON string with entry IDs of added memories
    """
    try:
        if not memories:
            return json.dumps({'ok': False, 'error': 'memories list is required'})
        
        memories_created = 0
        for mem in memories:
            if not mem.get('lossless_restatement'):
                continue
            
            res = gitmem_app.command_handler.execute(
                command_name="add_memory",
                actor_id=_default_user_id,
                workspace_id=_current_workspace_id,
                payload={
                    "repo_id": agent_id,
                    "text": mem.get('lossless_restatement'),
                    "metadata": {
                        "keywords": mem.get('keywords', []),
                        "timestamp": mem.get('timestamp'),
                        "location": mem.get('location'),
                        "persons": mem.get('persons', []),
                        "entities": mem.get('entities', []),
                        "topic": mem.get('topic')
                    }
                },
                skip_auth=True
            )
            if res.get("status") == "success":
                memories_created += res.get("data", {}).get("memories_added", 0)
        
        return json.dumps({
            'ok': True,
            'message': 'memories_added',
            'agent_id': agent_id,
            'entries_added': memories_created,
            'entry_ids': [] # V2 doesn't return these yet
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def search_memory(
    agent_id: str,
    query: str,
    top_k: int = 5,
    enable_reflection: bool = False
) -> str:
    """
    Search memories using hybrid retrieval (semantic + keyword + structured search).
    
    Uses HybridRetriever to find relevant memory entries combining:
    - Semantic vector similarity
    - Keyword/BM25-style matching
    - Structured metadata filtering
    
    Args:
        agent_id: Unique identifier for the agent
        query: Search query text
        top_k: Number of results to return (default: 5)
        enable_reflection: Enable reflection-based additional retrieval (default: False)
    
    Returns:
        JSON string with search results including memory entries
    """
    try:
        res = gitmem_app.command_handler.execute(
            command_name="retrieve_context",
            actor_id=_default_user_id,
            workspace_id=_current_workspace_id,
            payload={
                "repo_id": agent_id,
                "query": query,
                "max_tokens": top_k * 100 # Rough estimate
            },
            skip_auth=True
        )
        
        if res.get("status") != "success":
            return json.dumps({'ok': False, 'error': res.get('error')})
            
        data = res.get("data", {})
        results = data.get("sources", [])
        
        return json.dumps({
            'ok': True,
            'agent_id': agent_id,
            'query': query,
            'results_count': len(results),
            'results': results
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def get_context_answer(
    agent_id: str,
    question: str
) -> str:
    """
    Get a context-aware answer using GitMem V2 hybrid retrieval.

    Full Q&A flow: Query -> HybridRetrieval -> AnswerGenerator -> Response.
    Returns retrieved memory context and the sources used.

    Args:
        agent_id: Unique identifier for the agent (maps to repo_id in GitMem V2)
        question: The question to answer using memory context

    Returns:
        JSON string with the context string and sources used
    """
    try:
        res = gitmem_app.command_handler.execute(
            command_name="retrieve_context",
            actor_id=_default_user_id,
            workspace_id=_current_workspace_id,
            payload={
                "repo_id": agent_id,
                "query": question,
                "max_tokens": 2000
            },
            skip_auth=True
        )

        if res.get("status") != "success":
            return json.dumps({"ok": False, "error": res.get("error", "Retrieval failed")})

        data = res.get("data", {})
        context_string = data.get("context_string", "")
        sources = data.get("sources", [])

        contexts_used = [
            {
                "entry_id": src.get("id"),
                "content": src.get("content"),
                "type": src.get("type"),
                "created_at": src.get("created_at"),
                "importance": src.get("importance")
            }
            for src in sources[:5]
        ]

        return json.dumps({
            "ok": True,
            "agent_id": agent_id,
            "question": question,
            "context_string": context_string,
            "memories_used": data.get("memories_used", len(contexts_used)),
            "tokens_used": data.get("tokens_used", 0),
            "contexts_used": contexts_used
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
async def update_memory_entry(
    agent_id: str,
    entry_id: str,
    updates: Dict[str, Any]
) -> str:
    """
    Update an existing memory entry in GitMem V2 (Supabase + ChromaDB).

    You can update the content and/or metadata fields.

    Args:
        agent_id: Unique identifier for the agent (maps to repo_id in GitMem V2)
        entry_id: The ID of the memory entry to update (gitmem_memories.id)
        updates: Dictionary of fields to update. Supported keys:
                 - content: New text content (also re-embeds in ChromaDB)
                 - metadata: Dict of metadata to merge
                 - tags: New list of tags
                 - importance: New importance score (0.0-1.0)
                 - type: New memory type string

    Returns:
        JSON string with update status
    """
    try:
        if not updates:
            return json.dumps({"ok": False, "error": "updates dict is required"})

        db = gitmem_app.supabase_client
        if not db:
            return json.dumps({"ok": False, "error": "Database not available"})

        # Build the Supabase update payload — only include recognised columns
        patch: Dict[str, Any] = {}
        if "content" in updates:
            patch["content"] = updates["content"]
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            patch["metadata"] = updates["metadata"]
        if "tags" in updates:
            patch["tags"] = updates["tags"]
        if "importance" in updates:
            patch["importance"] = float(updates["importance"])
        if "type" in updates:
            patch["type"] = updates["type"]

        if not patch:
            return json.dumps({"ok": False, "error": "No valid update fields provided"})

        res = db.table("gitmem_memories").update(patch).eq("id", entry_id).eq("repo_id", agent_id).execute()

        if not res.data:
            return json.dumps({"ok": False, "error": "Entry not found or not updated"})

        # If content was updated, also refresh the ChromaDB vector
        if "content" in patch and gitmem_app.vector_engine:
            try:
                meta_for_vec = patch.get("metadata") or {}
                gitmem_app.vector_engine.update_memory(
                    memory_id=entry_id,
                    content=patch["content"],
                    metadata=meta_for_vec
                )
            except Exception as vec_err:
                # Vector update failure is non-fatal — Supabase is source of truth
                print(f"[MCP] Warning: ChromaDB update failed for {entry_id}: {vec_err}")

        return json.dumps({
            "ok": True,
            "message": "memory_updated",
            "agent_id": agent_id,
            "entry_id": entry_id,
            "fields_updated": list(patch.keys())
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
async def delete_memory_entries(
    agent_id: str,
    entry_ids: List[str]
) -> str:
    """
    Delete memory entries from GitMem V2 (Supabase + ChromaDB) by their entry IDs.

    This permanently removes memory entries from both the relational store and
    the vector store.

    Args:
        agent_id: Unique identifier for the agent (maps to repo_id in GitMem V2)
        entry_ids: List of entry IDs to delete (gitmem_memories.id values)

    Returns:
        JSON string with deletion status
    """
    try:
        if not entry_ids:
            return json.dumps({"ok": False, "error": "entry_ids list is required"})

        db = gitmem_app.supabase_client
        deleted_count = 0

        # 1. Delete from Supabase (source of truth)
        if db:
            try:
                res = (
                    db.table("gitmem_memories")
                    .delete()
                    .in_("id", entry_ids)
                    .eq("repo_id", agent_id)
                    .execute()
                )
                deleted_count = len(res.data) if res.data else len(entry_ids)
            except Exception as db_err:
                return json.dumps({"ok": False, "error": f"Database delete failed: {db_err}"})

        # 2. Delete from ChromaDB vector store (best-effort)
        if gitmem_app.vector_engine:
            for eid in entry_ids:
                try:
                    gitmem_app.vector_engine.delete_memory(memory_id=eid)
                except Exception as vec_err:
                    # Vector deletion failure is non-fatal
                    print(f"[MCP] Warning: ChromaDB delete failed for {eid}: {vec_err}")

        return json.dumps({
            "ok": True,
            "message": "memories_deleted",
            "agent_id": agent_id,
            "deleted_count": deleted_count,
            "entry_ids": entry_ids
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
async def list_all_memories(agent_id: str, limit: int = 50) -> str:
    """
    List all memory entries for an agent from GitMem V2.

    Args:
        agent_id: Unique identifier for the agent (maps to repo_id in GitMem V2)
        limit: Maximum number of entries to return (default: 50, max: 200)

    Returns:
        JSON string with list of all memory entries
    """
    try:
        db = gitmem_app.supabase_client
        if not db:
            return json.dumps({"ok": False, "error": "Database not available"})

        safe_limit = min(int(limit), 200)

        res = (
            db.table("gitmem_memories")
            .select("id, content, type, importance, tags, metadata, created_at, agent_id, repo_id, workspace_id")
            .eq("repo_id", agent_id)
            .order("created_at", desc=True)
            .limit(safe_limit)
            .execute()
        )

        memories_data = res.data or []

        # Also get the total count for the agent
        count_res = (
            db.table("gitmem_memories")
            .select("id", count="exact")
            .eq("repo_id", agent_id)
            .execute()
        )
        total = count_res.count if hasattr(count_res, "count") and count_res.count is not None else len(memories_data)

        results = []
        for mem in memories_data:
            results.append({
                "entry_id": mem.get("id"),
                "content": mem.get("content"),
                "type": mem.get("type"),
                "importance": mem.get("importance"),
                "tags": mem.get("tags", []),
                "metadata": mem.get("metadata", {}),
                "created_at": mem.get("created_at"),
                "agent_id": mem.get("agent_id"),
                "repo_id": mem.get("repo_id"),
                "workspace_id": mem.get("workspace_id")
            })

        return json.dumps({
            "ok": True,
            "agent_id": agent_id,
            "total_memories": total,
            "returned": len(results),
            "memories": results
        })
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


# ============================================================================
# MCP RESOURCES - Expose data sources for Claude to read
# ============================================================================

@mcp.resource("memory://agents/list")
async def list_active_agents() -> str:
    """List all registered agents from the mcp_agents table."""
    try:
        agents = _agents_service.list_agents(user_id=_default_user_id)
        return json.dumps({
            "agents": agents,
            "count": len(agents)
        })
    except Exception as e:
        return json.dumps({"agents": [], "count": 0, "error": str(e)})


@mcp.resource("memory://config/info")
async def get_server_info() -> str:
    """Get information about the MCP Memory Server."""
    return json.dumps({
        'name': 'Manhattan Memory MCP Server',
        'version': '2.0.0',
        'description': 'MCP server for Memory CRUD operations with agent management',
        'current_agent': _current_agent_id,
        'available_tools': {
            'agent_management': [
                'register_agent',
                'list_my_agents',
                'get_agent_details',
                'update_agent_info',
                'remove_agent',
                'switch_to_agent',
                'current_agent'
            ],
            'memory_operations': [
                'create_memory',
                'process_raw_dialogues',
                'add_memory_direct',
                'search_memory',
                'get_context_answer',
                'update_memory_entry',
                'delete_memory_entries',
                'list_all_memories'
            ]
        }
    })


# ============================================================================
# Main entry point
# ============================================================================

def main():
    """Initialize and run the MCP server."""
    print("=" * 60, file=sys.stderr)
    print("  Manhattan Memory MCP Server v2.0", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(file=sys.stderr)
    print("Agent Management Tools:", file=sys.stderr)
    print("  * register_agent       - Create a new memory agent", file=sys.stderr)
    print("  * list_my_agents       - List all your agents", file=sys.stderr)
    print("  * get_agent_details    - Get agent info", file=sys.stderr)
    print("  * update_agent_info    - Update agent details", file=sys.stderr)
    print("  * remove_agent         - Delete an agent", file=sys.stderr)
    print("  * switch_to_agent      - Switch context to an agent", file=sys.stderr)
    print("  * current_agent        - Get current agent", file=sys.stderr)
    print(file=sys.stderr)
    print("Memory Operations:", file=sys.stderr)
    print("  * create_memory        - Initialize memory system", file=sys.stderr)
    print("  * process_raw_dialogues - Process dialogues via LLM", file=sys.stderr)
    print("  * add_memory_direct    - Add memories directly", file=sys.stderr)
    print("  * search_memory        - Hybrid search", file=sys.stderr)
    print("  * get_context_answer   - Q&A with memory context", file=sys.stderr)
    print("  * update_memory_entry  - Update memory", file=sys.stderr)
    print("  * delete_memory_entries - Delete memories", file=sys.stderr)
    print("  * list_all_memories    - List all memories", file=sys.stderr)
    print(file=sys.stderr)
    import argparse
    
    parser = argparse.ArgumentParser(description='Manhattan Memory MCP Server')
    parser.add_argument('--transport', default='stdio', choices=['stdio', 'sse'],
                      help='Transport protocol to use (default: stdio)')
    parser.add_argument('--host', default='0.0.0.0',
                      help='Host to bind to for SSE (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                      help='Port to listen on for SSE (default: 8000)')
    
    args = parser.parse_args()
    
    if args.transport == 'sse':
        print(f"Starting Manhattan Memory MCP Server on http://{args.host}:{args.port} (SSE)", file=sys.stderr)
        print("Local resource access enabled.", file=sys.stderr)
        mcp.settings.port = args.port
        mcp.settings.host = args.host
        mcp.run(transport="sse")
    else:
        # Check standard input/output for stdio
        print("Running on stdio transport...", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    # Ensure all required environment variables are set or warn
    if not os.getenv("MANHATTAN_API_KEY") and not os.getenv("SUPABASE_URL"):
        print("Warning: MANHATTAN_API_KEY or SUPABASE credentials not found in environment.", file=sys.stderr)
        print("Agent management and some features may be limited.", file=sys.stderr)
        
    main()
