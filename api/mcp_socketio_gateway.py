"""
MCP Socket.IO Gateway - Remote MCP Server via WebSocket

This module exposes the MCP memory tools via Socket.IO, allowing AI agents
to connect remotely using only a URL (no client file needed).

Usage:
    AI agents connect via Socket.IO to the /mcp namespace and use:
    - mcp:get_tools - Get available tools and their schemas
    - mcp:call_tool - Execute a tool with arguments

Example Client:
    import socketio
    sio = socketio.Client()
    sio.connect("https://themanhattanproject.ai", namespaces=["/mcp"])
    
    tools = sio.call("mcp:get_tools", {"api_key": "your-key"}, namespace="/mcp")
    result = sio.call("mcp:call_tool", {
        "api_key": "your-key",
        "tool": "search_memory",
        "arguments": {"agent_id": "my-agent", "query": "user preferences"}
    }, namespace="/mcp")
"""

import os
import sys
import json
import asyncio
import functools
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask_socketio import SocketIO, emit, disconnect
from flask import request

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import key utilities for API key verification
from key_utils import hash_key

# Supabase for API key validation (optional - falls back to dev mode if unavailable)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

_supabase = None
try:
    from supabase import create_client
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("[MCP Gateway] Supabase client initialized for API key validation")
except ImportError as e:
    print(f"[MCP Gateway] Supabase not available: {e}. Using development mode for auth.")
except Exception as e:
    print(f"[MCP Gateway] Supabase init error: {e}. Using development mode for auth.")

# Import the MCP tools from mcp_memory_client
from mcp_memory_client import mcp

# Store connected clients
_connected_clients: Dict[str, Dict[str, Any]] = {}


def verify_api_key(api_key: Optional[str]) -> Dict[str, Any]:
    """
    Verify an API key against the database.
    
    Returns:
        Dict with 'ok': True/False and 'user_id' if valid
    """
    if not api_key:
        return {"ok": False, "error": "API key required"}
    
    if not _supabase:
        # Development mode - allow if key starts with 'sk-'
        if api_key.startswith("sk-"):
            return {"ok": True, "user_id": "dev-user", "mode": "development"}
        return {"ok": False, "error": "Database not configured"}
    
    try:
        # Hash the key and look it up
        hashed = hash_key(api_key)
        
        result = _supabase.table("api_keys").select("id, user_id, status, permissions").eq("hashed_key", hashed).execute()
        
        if not result.data:
            # Try legacy key column (some old keys stored hash there)
            result = _supabase.table("api_keys").select("id, user_id, status, permissions").eq("key", hashed).execute()
        
        if result.data and len(result.data) > 0:
            key_record = result.data[0]
            if key_record.get("status") == "active":
                return {
                    "ok": True,
                    "user_id": key_record.get("user_id"),
                    "permissions": key_record.get("permissions", {})
                }
            else:
                return {"ok": False, "error": "API key is not active"}
        
        return {"ok": False, "error": "Invalid API key"}
    
    except Exception as e:
        print(f"[MCP Gateway] API key verification error: {e}")
        return {"ok": False, "error": "Verification failed"}


def get_tools_schema() -> Dict[str, Any]:
    """
    Extract tool schemas from the FastMCP server.
    
    Returns a dictionary of tool names to their schemas.
    """
    tools = {}
    
    # Get tools from FastMCP's internal registry
    if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, '_tools'):
        for name, tool in mcp._tool_manager._tools.items():
            tools[name] = {
                "name": name,
                "description": tool.description if hasattr(tool, 'description') else "",
                "parameters": tool.parameters if hasattr(tool, 'parameters') else {}
            }
    elif hasattr(mcp, 'list_tools'):
        # Try alternative method
        try:
            tool_list = asyncio.run(mcp.list_tools())
            for tool in tool_list:
                tools[tool.name] = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                }
        except Exception as e:
            print(f"[MCP Gateway] Error listing tools: {e}")
    
    # Fallback: manually define core tools if detection fails
    if not tools:
        tools = _get_fallback_tools_schema()
    
    return tools


def _get_fallback_tools_schema() -> Dict[str, Any]:
    """Fallback tool definitions if auto-detection fails."""
    return {
        "search_memory": {
            "name": "search_memory",
            "description": "Search memories using hybrid retrieval (semantic + keyword)",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent identifier"},
                    "query": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Max results", "default": 5},
                    "enable_reflection": {"type": "boolean", "default": False}
                },
                "required": ["agent_id", "query"]
            }
        },
        "add_memory_direct": {
            "name": "add_memory_direct",
            "description": "Store memories directly without LLM processing",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "memories": {"type": "array", "items": {"type": "object"}}
                },
                "required": ["agent_id", "memories"]
            }
        },
        "auto_remember": {
            "name": "auto_remember",
            "description": "Automatically extract and store facts from user message",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "user_message": {"type": "string"}
                },
                "required": ["agent_id", "user_message"]
            }
        },
        "get_context_answer": {
            "name": "get_context_answer",
            "description": "Get AI-generated answer using memory context",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "question": {"type": "string"}
                },
                "required": ["agent_id", "question"]
            }
        },
        "session_start": {
            "name": "session_start",
            "description": "Initialize a new conversation session",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "auto_pull_context": {"type": "boolean", "default": True}
                }
            }
        },
        "session_end": {
            "name": "session_end",
            "description": "End the current session and sync memories",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "conversation_summary": {"type": "string"},
                    "key_points": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "agent_stats": {
            "name": "agent_stats",
            "description": "Get comprehensive statistics for an agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"}
                },
                "required": ["agent_id"]
            }
        },
        "create_agent": {
            "name": "create_agent",
            "description": "Create a new agent in the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string"},
                    "agent_slug": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["agent_name", "agent_slug"]
            }
        },
        "list_agents": {
            "name": "list_agents",
            "description": "List all agents owned by the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"}
                }
            }
        }
    }


async def execute_tool_async(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute an MCP tool by name with given arguments."""
    # Get the tool function from FastMCP
    tool_fn = None
    
    if hasattr(mcp, '_tool_manager') and hasattr(mcp._tool_manager, '_tools'):
        tool = mcp._tool_manager._tools.get(tool_name)
        if tool:
            tool_fn = tool.fn if hasattr(tool, 'fn') else tool
    
    if not tool_fn:
        # Try to get function from module globals
        import mcp_memory_client
        tool_fn = getattr(mcp_memory_client, tool_name, None)
    
    if not tool_fn:
        return {"ok": False, "error": f"Tool '{tool_name}' not found"}
    
    try:
        # Execute the tool
        if asyncio.iscoroutinefunction(tool_fn):
            result = await tool_fn(**arguments)
        else:
            result = tool_fn(**arguments)
        
        # Parse JSON result if it's a string
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"ok": True, "result": result}
        
        return result
    
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Synchronous wrapper for tool execution."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(execute_tool_async(tool_name, arguments))


def init_mcp_socketio(socketio: SocketIO):
    """
    Initialize Socket.IO event handlers for MCP.
    Call this from your main Flask app after creating SocketIO instance.
    """
    
    @socketio.on("connect", namespace="/mcp")
    def handle_connect():
        """Handle new WebSocket connection."""
        client_id = request.sid
        print(f"[MCP Gateway] Client connected: {client_id}")
        
        _connected_clients[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "authenticated": False
        }
        
        emit("connection_established", {
            "status": "connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Welcome to Manhattan MCP Gateway. Use mcp:get_tools to discover available tools."
        })
    
    @socketio.on("disconnect", namespace="/mcp")
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        client_id = request.sid
        print(f"[MCP Gateway] Client disconnected: {client_id}")
        
        if client_id in _connected_clients:
            del _connected_clients[client_id]
    
    @socketio.on("mcp:get_tools", namespace="/mcp")
    def handle_get_tools(data):
        """
        Tool discovery endpoint.
        
        Request: {"api_key": "sk-xxx"}
        Response: {"ok": true, "tools": {...}}
        """
        api_key = data.get("api_key") if data else None
        
        # Verify API key
        auth = verify_api_key(api_key)
        if not auth.get("ok"):
            return {"ok": False, "error": auth.get("error", "Authentication failed")}
        
        # Mark client as authenticated
        client_id = request.sid
        if client_id in _connected_clients:
            _connected_clients[client_id]["authenticated"] = True
            _connected_clients[client_id]["user_id"] = auth.get("user_id")
        
        # Return tool schemas
        tools = get_tools_schema()
        return {
            "ok": True,
            "tools": tools,
            "tool_count": len(tools),
            "message": "Use mcp:call_tool to execute a tool"
        }
    
    @socketio.on("mcp:call_tool", namespace="/mcp")
    def handle_call_tool(data):
        """
        Tool execution endpoint.
        
        Request: {
            "api_key": "sk-xxx",
            "tool": "search_memory",
            "arguments": {"agent_id": "...", "query": "..."}
        }
        Response: Tool result or error
        """
        if not data:
            return {"ok": False, "error": "No data provided"}
        
        api_key = data.get("api_key")
        tool_name = data.get("tool")
        arguments = data.get("arguments", {})
        
        # Verify API key
        auth = verify_api_key(api_key)
        if not auth.get("ok"):
            return {"ok": False, "error": auth.get("error", "Authentication failed")}
        
        # Validate tool name
        if not tool_name:
            return {"ok": False, "error": "Tool name required"}
        
        # Execute the tool
        try:
            result = execute_tool(tool_name, arguments)
            return result
        except Exception as e:
            print(f"[MCP Gateway] Tool execution error: {e}")
            return {"ok": False, "error": str(e)}
    
    @socketio.on("mcp:ping", namespace="/mcp")
    def handle_ping():
        """Health check ping/pong."""
        return {
            "ok": True,
            "pong": True,
            "timestamp": datetime.now().isoformat()
        }
    
    @socketio.on("mcp:get_instructions", namespace="/mcp")
    def handle_get_instructions(data=None):
        """
        Get MCP instructions for AI agents.
        
        Response: Instructions for how to use the memory system
        """
        api_key = data.get("api_key") if data else None
        
        auth = verify_api_key(api_key)
        if not auth.get("ok"):
            return {"ok": False, "error": auth.get("error", "Authentication failed")}
        
        return {
            "ok": True,
            "instructions": """
Manhattan Memory MCP - Remote AI Agent Instructions

This is a PERSISTENT MEMORY SYSTEM for storing and retrieving information.

MANDATORY WORKFLOW:
1. Call session_start at conversation beginning
2. Call search_memory BEFORE answering user questions
3. Call add_memory_direct when user shares new information
4. Call auto_remember after every user message
5. Call session_end when conversation ends

MEMORY TRIGGERS - ALWAYS STORE:
- User's name, preferences, interests
- Important dates, deadlines, events
- Technical details, project information
- Personal context shared by user
- Decisions, agreements, action items

CONNECTION EXAMPLE:
    import socketio
    sio = socketio.Client()
    sio.connect("https://themanhattanproject.ai", namespaces=["/mcp"])
    result = sio.call("mcp:call_tool", {
        "api_key": "your-key",
        "tool": "search_memory",
        "arguments": {"agent_id": "your-agent", "query": "user info"}
    }, namespace="/mcp")
""",
            "default_agent_id": "84aab1f8-3ea9-4c6a-aa3c-cd8eaa274a5e"
        }
    
    print("[MCP Gateway] Socket.IO handlers initialized on /mcp namespace")
    return socketio
