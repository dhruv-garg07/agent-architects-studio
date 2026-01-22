#!/usr/bin/env python3
"""
Manhattan Memory MCP Server (Remote API Client)

This is a LIGHTWEIGHT MCP server that connects to the hosted Manhattan API.
Users don't need to clone the full repository - just this single file!

Setup:
    1. pip install mcp httpx python-dotenv
    2. Set your API_KEY environment variable
    3. Add to Claude Desktop config (see README)
    4. Restart Claude Desktop

Configuration:
    Set these environment variables:
    - MANHATTAN_API_KEY: Your API key for authentication
    - MANHATTAN_API_URL: API base URL (default: https://agent-architects-studio.onrender.com/manhattan)

Usage:
    python mcp_memory_client.py

Author: Agent Architects Studio
License: MIT
"""

import os
import sys
import json
import asyncio
from typing import Any, Optional, List, Dict

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("=" * 50)
    print("ERROR: MCP package not installed!")
    print("Install with: pip install mcp")
    print("=" * 50)
    sys.exit(1)

# Import HTTP client
try:
    import httpx
except ImportError:
    print("=" * 50)
    print("ERROR: httpx package not installed!")
    print("Install with: pip install httpx")
    print("=" * 50)
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

# Default API URL - hosted Manhattan Project API
DEFAULT_API_URL = "https://www.themanhattanproject.ai"

# Get configuration from environment
API_URL = os.getenv("MANHATTAN_API_URL", DEFAULT_API_URL)
API_KEY = os.getenv("MANHATTAN_API_KEY", "sk-tg5T-vIyYnuprwVPcgoHGfX37HBsfPwAvHkV3WFyhkE")

# Timeout for API requests (seconds)
REQUEST_TIMEOUT = 120.0

# Initialize FastMCP server
mcp = FastMCP("manhattan-memory-client")


# ============================================================================
# HTTP Client Helper
# ============================================================================

async def call_api(endpoint: str, payload: dict) -> dict:
    """Make an authenticated request to the Manhattan API."""
    url = f"{API_URL}/{endpoint}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "ok": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except httpx.RequestError as e:
            return {
                "ok": False,
                "error": f"Request failed: {str(e)}"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)
            }


# ============================================================================
# MCP TOOLS - Memory CRUD Operations (via Remote API)
# ============================================================================

@mcp.tool()
async def create_memory(agent_id: str, clear_db: bool = False) -> str:
    """
    Create/initialize a memory system for an agent.
    
    Creates a ChromaDB collection for storing memory entries on the hosted server.
    Set clear_db to True to clear existing memories.
    
    Args:
        agent_id: Unique identifier for the agent (e.g., 'my-chatbot', 'customer-support')
        clear_db: Whether to clear existing memories (default: False)
    
    Returns:
        JSON string with creation status
    """
    result = await call_api("create_memory", {
        "agent_id": agent_id,
        "clear_db": clear_db
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def process_raw_dialogues(
    agent_id: str,
    dialogues: List[Dict[str, str]]
) -> str:
    """
    Process raw dialogues through LLM to extract structured memory entries.
    
    The server will use AI to extract facts, entities, timestamps, and keywords
    from the dialogues and store them as searchable memories.
    
    Args:
        agent_id: Unique identifier for the agent
        dialogues: List of dialogue objects, each with keys:
                   - speaker: Name of the speaker (e.g., "Alice", "User")
                   - content: The dialogue content
                   - timestamp: (optional) ISO8601 timestamp
    
    Example dialogues:
        [
            {"speaker": "Alice", "content": "Let's meet at Starbucks tomorrow at 2pm"},
            {"speaker": "Bob", "content": "Sure, I'll bring the project documents"}
        ]
    
    Returns:
        JSON string with processing status and count of memories created
    """
    result = await call_api("process_raw", {
        "agent_id": agent_id,
        "dialogues": dialogues
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def add_memory_direct(
    agent_id: str,
    memories: List[Dict[str, Any]]
) -> str:
    """
    Directly save pre-structured memory entries without LLM processing.
    
    Use this when you already have structured data and want to bypass AI extraction.
    Faster than process_raw_dialogues but requires proper formatting.
    
    Args:
        agent_id: Unique identifier for the agent
        memories: List of memory objects, each with keys:
                  - lossless_restatement: (required) Self-contained fact statement
                  - keywords: (optional) List of keywords for search
                  - timestamp: (optional) ISO8601 timestamp
                  - location: (optional) Location string
                  - persons: (optional) List of person names mentioned
                  - entities: (optional) List of entities (products, companies, etc.)
                  - topic: (optional) Topic phrase
    
    Example memory:
        {
            "lossless_restatement": "Alice scheduled a meeting with Bob at Starbucks on January 22, 2025 at 2pm",
            "keywords": ["meeting", "Starbucks", "schedule"],
            "persons": ["Alice", "Bob"],
            "location": "Starbucks",
            "topic": "meeting scheduling"
        }
    
    Returns:
        JSON string with entry IDs of added memories
    """
    result = await call_api("add_memory", {
        "agent_id": agent_id,
        "memories": memories
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def search_memory(
    agent_id: str,
    query: str,
    top_k: int = 5,
    enable_reflection: bool = False
) -> str:
    """
    Search memories using hybrid retrieval (semantic + keyword search).
    
    Combines vector similarity search with keyword matching to find
    the most relevant memories for your query.
    
    Args:
        agent_id: Unique identifier for the agent
        query: Natural language search query (e.g., "When is the meeting?")
        top_k: Maximum number of results to return (default: 5)
        enable_reflection: Enable multi-round retrieval for better results (default: False)
    
    Returns:
        JSON string with search results containing memory entries
    """
    result = await call_api("read_memory", {
        "agent_id": agent_id,
        "query": query,
        "top_k": top_k,
        "enable_reflection": enable_reflection
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_context_answer(
    agent_id: str,
    question: str
) -> str:
    """
    Ask a question and get an AI-generated answer using memory context.
    
    Full Q&A flow: Your question → Memory Search → AI Answer Generation.
    Returns both the answer and the memory contexts that were used.
    
    Args:
        agent_id: Unique identifier for the agent
        question: Natural language question (e.g., "What did Alice and Bob discuss?")
    
    Returns:
        JSON string with the answer and contexts used
    """
    result = await call_api("get_context", {
        "agent_id": agent_id,
        "question": question
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_memory_entry(
    agent_id: str,
    entry_id: str,
    updates: Dict[str, Any]
) -> str:
    """
    Update an existing memory entry.
    
    You can update the content (lossless_restatement) and/or metadata fields.
    
    Args:
        agent_id: Unique identifier for the agent
        entry_id: The ID of the memory entry to update (returned when creating memories)
        updates: Dictionary of fields to update. Available fields:
                 - lossless_restatement: New content
                 - timestamp: New timestamp
                 - location: New location
                 - persons: New list of persons
                 - entities: New list of entities
                 - topic: New topic
                 - keywords: New list of keywords
    
    Returns:
        JSON string with update status
    """
    result = await call_api("update_memory", {
        "agent_id": agent_id,
        "entry_id": entry_id,
        "updates": updates
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_memory_entries(
    agent_id: str,
    entry_ids: List[str]
) -> str:
    """
    Delete memory entries by their IDs.
    
    This permanently removes the specified memories from the agent's storage.
    
    Args:
        agent_id: Unique identifier for the agent
        entry_ids: List of entry IDs to delete
    
    Returns:
        JSON string with deletion status
    """
    result = await call_api("delete_memory", {
        "agent_id": agent_id,
        "entry_ids": entry_ids
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def chat_with_agent(
    agent_id: str,
    message: str
) -> str:
    """
    Send a chat message to an agent and get a response.
    
    The agent will use its memory context to provide relevant answers.
    This also saves the conversation to memory for future reference.
    
    Args:
        agent_id: Unique identifier for the agent
        message: Your message to the agent
    
    Returns:
        JSON string with the agent's response
    """
    result = await call_api("agent_chat", {
        "agent_id": agent_id,
        "message": message
    })
    return json.dumps(result, indent=2)


# ============================================================================
# MCP TOOLS - Agent CRUD Operations (via Remote API)
# ============================================================================

async def call_api_get(endpoint: str, params: dict = None) -> dict:
    """Make an authenticated GET request to the Manhattan API."""
    url = f"{API_URL}/{endpoint}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "ok": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except httpx.RequestError as e:
            return {
                "ok": False,
                "error": f"Request failed: {str(e)}"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)
            }


@mcp.tool()
async def create_agent(
    agent_name: str,
    agent_slug: str,
    permissions: Dict[str, Any] = None,
    limits: Dict[str, Any] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new agent in the Manhattan system.
    
    Creates an agent record in Supabase and initializes ChromaDB collections
    for storing chat history and file data.
    
    Args:
        agent_name: Human-readable name for the agent (e.g., 'Customer Support Bot')
        agent_slug: URL-friendly identifier (e.g., 'customer-support-bot')
        permissions: Dict of permissions the agent has (default: {})
        limits: Dict of rate limits/quotas for the agent (default: {})
        description: Optional description of the agent's purpose
        metadata: Optional additional metadata dictionary
    
    Returns:
        JSON string with the created agent record including agent_id
    
    Example:
        create_agent(
            agent_name="My Assistant",
            agent_slug="my-assistant",
            permissions={"chat": True, "memory": True},
            limits={"requests_per_day": 1000},
            description="A helpful assistant for my project"
        )
    """
    payload = {
        "agent_name": agent_name,
        "agent_slug": agent_slug,
        "permissions": permissions or {},
        "limits": limits or {},
    }
    
    if description:
        payload["description"] = description
    if metadata:
        payload["metadata"] = metadata
    
    result = await call_api("create_agent", payload)
    return json.dumps(result, indent=2)


@mcp.tool()
async def list_agents(
    status: Optional[str] = None
) -> str:
    """
    List all agents owned by the authenticated user.
    
    Returns a list of all agents associated with your API key.
    Optionally filter by status.
    
    Args:
        status: Optional filter by status ('active', 'disabled', 'pending')
    
    Returns:
        JSON string with list of agent records
    """
    params = {}
    if status:
        params["status"] = status
    
    result = await call_api_get("list_agents", params)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_agent(
    agent_id: str
) -> str:
    """
    Get details of a specific agent by ID.
    
    Retrieves the full agent record including configuration,
    status, and metadata.
    
    Args:
        agent_id: Unique identifier of the agent to retrieve
    
    Returns:
        JSON string with the agent record
    """
    # Note: The API expects agent_id in the request body for GET
    result = await call_api("get_agent", {"agent_id": agent_id})
    return json.dumps(result, indent=2)


@mcp.tool()
async def update_agent(
    agent_id: str,
    updates: Dict[str, Any]
) -> str:
    """
    Update an existing agent's configuration.
    
    Only specific fields can be updated: agent_name, agent_slug, 
    status, description, and metadata.
    
    Args:
        agent_id: Unique identifier of the agent to update
        updates: Dictionary of fields to update. Allowed fields:
                 - agent_name: New name for the agent
                 - agent_slug: New URL-friendly identifier
                 - status: New status ('active', 'disabled', 'pending')
                 - description: New description
                 - metadata: New metadata dictionary
    
    Returns:
        JSON string with the updated agent record
    
    Example:
        update_agent(
            agent_id="abc-123",
            updates={
                "agent_name": "Updated Assistant",
                "description": "An improved version of my assistant"
            }
        )
    """
    result = await call_api("update_agent", {
        "agent_id": agent_id,
        "updates": updates
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def disable_agent(
    agent_id: str
) -> str:
    """
    Soft delete (disable) an agent.
    
    This sets the agent's status to 'disabled' without permanently
    deleting it. The agent can be re-enabled later using enable_agent.
    
    Args:
        agent_id: Unique identifier of the agent to disable
    
    Returns:
        JSON string with success status
    """
    result = await call_api("disable_agent", {
        "agent_id": agent_id
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def enable_agent(
    agent_id: str
) -> str:
    """
    Enable a previously disabled agent.
    
    Restores an agent's status to 'active' so it can be used again.
    
    Args:
        agent_id: Unique identifier of the agent to enable
    
    Returns:
        JSON string with success status
    """
    result = await call_api("enable_agent", {
        "agent_id": agent_id
    })
    return json.dumps(result, indent=2)


@mcp.tool()
async def delete_agent(
    agent_id: str
) -> str:
    """
    Permanently delete an agent.
    
    WARNING: This action is irreversible! It will permanently delete:
    - The agent record from the database
    - All associated ChromaDB collections (chat history, file data)
    - All stored memories for this agent
    
    Use disable_agent for a reversible soft-delete instead.
    
    Args:
        agent_id: Unique identifier of the agent to delete
    
    Returns:
        JSON string with deletion status
    """
    result = await call_api("delete_agent", {
        "agent_id": agent_id
    })
    return json.dumps(result, indent=2)


# ============================================================================
# MCP RESOURCES - Information about the server
# ============================================================================

@mcp.resource("memory://server/info")
async def get_server_info() -> str:
    """Get information about the MCP Memory Server."""
    return json.dumps({
        "name": "Manhattan Memory MCP Client",
        "version": "1.0.0",
        "description": "Lightweight MCP client for Manhattan Memory API",
        "api_url": API_URL,
        "authenticated": bool(API_KEY),
        "available_tools": [
            "create_memory",
            "process_raw_dialogues",
            "add_memory_direct",
            "search_memory",
            "get_context_answer",
            "update_memory_entry",
            "delete_memory_entries",
            "chat_with_agent",
            "create_agent",
            "list_agents",
            "get_agent",
            "update_agent",
            "disable_agent",
            "enable_agent",
            "delete_agent"
        ]
    }, indent=2)


@mcp.resource("memory://server/health")
async def check_health() -> str:
    """Check if the remote API is accessible."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to ping the server
            response = await client.get(f"{API_URL.rsplit('/manhattan', 1)[0]}/ping")
            if response.status_code == 200:
                return json.dumps({"status": "healthy", "api_url": API_URL})
            else:
                return json.dumps({"status": "unhealthy", "code": response.status_code})
    except Exception as e:
        return json.dumps({"status": "unreachable", "error": str(e)})


# ============================================================================
# Main entry point
# ============================================================================

def main():
    """Initialize and run the MCP server."""
    print("=" * 60)
    print("  Manhattan Memory MCP Client")
    print("=" * 60)
    print(f"  API URL: {API_URL}")
    print(f"  API Key: {'✓ Configured' if API_KEY else '✗ Not set (set MANHATTAN_API_KEY)'}")
    print()
    print("  Available Tools (Memory):")
    print("    • create_memory       - Initialize memory for an agent")
    print("    • process_raw_dialogues - Process dialogues via AI")
    print("    • add_memory_direct   - Direct memory save (no AI)")
    print("    • search_memory       - Hybrid search")
    print("    • get_context_answer  - Q&A with memory context")
    print("    • update_memory_entry - Update existing memory")
    print("    • delete_memory_entries - Delete memories")
    print("    • chat_with_agent     - Chat with agent")
    print()
    print("  Available Tools (Agent CRUD):")
    print("    • create_agent        - Create a new agent")
    print("    • list_agents         - List all agents for user")
    print("    • get_agent           - Get agent by ID")
    print("    • update_agent        - Update agent configuration")
    print("    • disable_agent       - Soft delete (disable) agent")
    print("    • enable_agent        - Re-enable a disabled agent")
    print("    • delete_agent        - Permanently delete an agent")
    print()
    print("  Running on stdio transport...")
    print("=" * 60)
    
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
