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

# Import SimpleMem components
try:
    from SimpleMem.main import create_system, SimpleMemSystem
    from SimpleMem.models.memory_entry import MemoryEntry, Dialogue
except ImportError as e:
    print(f"Error importing SimpleMem: {e}")
    print("Make sure SimpleMem module is available in the path")
    sys.exit(1)

# Initialize FastMCP server
mcp = FastMCP("manhattan-memory")

# Cache for SimpleMem systems per agent
_memory_systems_cache: Dict[str, SimpleMemSystem] = {}


def _get_or_create_memory_system(agent_id: str, clear_db: bool = False) -> SimpleMemSystem:
    """Get cached SimpleMem system or create new one for the agent."""
    if agent_id not in _memory_systems_cache or clear_db:
        _memory_systems_cache[agent_id] = create_system(agent_id=agent_id, clear_db=clear_db)
    return _memory_systems_cache[agent_id]


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
        memory_system = _get_or_create_memory_system(agent_id, clear_db=clear_db)
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
        
        memory_system = _get_or_create_memory_system(agent_id)
        
        memories_created = 0
        for dlg in dialogues:
            speaker = dlg.get('speaker', 'unknown')
            content = dlg.get('content', '')
            timestamp = dlg.get('timestamp')
            
            if content:
                memory_system.add_dialogue(
                    speaker=speaker,
                    content=content,
                    timestamp=timestamp
                )
                memories_created += 1
        
        memory_system.finalize()
        
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
        
        memory_system = _get_or_create_memory_system(agent_id)
        
        entries = []
        entry_ids = []
        for mem in memories:
            if not mem.get('lossless_restatement'):
                continue
            
            entry = MemoryEntry(
                lossless_restatement=mem.get('lossless_restatement'),
                keywords=mem.get('keywords', []),
                timestamp=mem.get('timestamp'),
                location=mem.get('location'),
                persons=mem.get('persons', []),
                entities=mem.get('entities', []),
                topic=mem.get('topic')
            )
            entries.append(entry)
            entry_ids.append(entry.entry_id)
        
        if entries:
            memory_system.vector_store.add_entries(entries)
        
        return json.dumps({
            'ok': True,
            'message': 'memories_added',
            'agent_id': agent_id,
            'entries_added': len(entries),
            'entry_ids': entry_ids
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
        memory_system = _get_or_create_memory_system(agent_id)
        
        contexts = memory_system.hybrid_retriever.retrieve(query, enable_reflection=enable_reflection)
        
        results = []
        for ctx in contexts[:top_k]:
            results.append({
                'entry_id': ctx.entry_id,
                'lossless_restatement': ctx.lossless_restatement,
                'keywords': ctx.keywords,
                'timestamp': ctx.timestamp,
                'location': ctx.location,
                'persons': ctx.persons,
                'entities': ctx.entities,
                'topic': ctx.topic
            })
        
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
    Get a context-aware answer using SimpleMem's ask function.
    
    Full Q&A flow: Query → HybridRetrieval → AnswerGenerator → Response.
    Returns both the LLM-generated answer and the memory contexts used.
    
    Args:
        agent_id: Unique identifier for the agent
        question: The question to answer using memory context
    
    Returns:
        JSON string with the answer and contexts used
    """
    try:
        memory_system = _get_or_create_memory_system(agent_id)
        
        answer = memory_system.ask(question)
        
        contexts = memory_system.hybrid_retriever.retrieve(question)
        contexts_used = [
            {
                'entry_id': ctx.entry_id,
                'lossless_restatement': ctx.lossless_restatement,
                'topic': ctx.topic
            }
            for ctx in contexts[:5]
        ]
        
        return json.dumps({
            'ok': True,
            'agent_id': agent_id,
            'question': question,
            'answer': answer,
            'contexts_used': contexts_used
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def update_memory_entry(
    agent_id: str,
    entry_id: str,
    updates: Dict[str, Any]
) -> str:
    """
    Update an existing memory entry in ChromaDB.
    
    You can update the document content (lossless_restatement) and/or
    metadata fields (timestamp, location, persons, entities, topic, keywords).
    
    Args:
        agent_id: Unique identifier for the agent
        entry_id: The ID of the memory entry to update
        updates: Dictionary of fields to update. Keys can be:
                 - lossless_restatement: New document content
                 - timestamp: New timestamp
                 - location: New location
                 - persons: New list of persons
                 - entities: New list of entities
                 - topic: New topic
                 - keywords: New list of keywords
    
    Returns:
        JSON string with update status
    """
    try:
        if not updates:
            return json.dumps({'ok': False, 'error': 'updates dict is required'})
        
        memory_system = _get_or_create_memory_system(agent_id)
        
        document_content = updates.get('lossless_restatement')
        
        metadata = {}
        updateable_metadata = ['timestamp', 'location', 'persons', 'entities', 'topic', 'keywords']
        for field in updateable_metadata:
            if field in updates:
                value = updates[field]
                if isinstance(value, list):
                    metadata[field] = json.dumps(value)
                else:
                    metadata[field] = value
        
        if document_content:
            memory_system.vector_store.rag.update_docs(
                agent_ID=agent_id,
                ids=[entry_id],
                documents=[document_content],
                metadatas=[metadata] if metadata else None
            )
        elif metadata:
            memory_system.vector_store.rag.update_doc_metadata(
                agent_ID=agent_id,
                ids=[entry_id],
                metadatas=[metadata]
            )
        
        return json.dumps({
            'ok': True,
            'message': 'memory_updated',
            'agent_id': agent_id,
            'entry_id': entry_id
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def delete_memory_entries(
    agent_id: str,
    entry_ids: List[str]
) -> str:
    """
    Delete memory entries from ChromaDB by their entry IDs.
    
    This permanently removes the memory entries from the agent's vector store.
    
    Args:
        agent_id: Unique identifier for the agent
        entry_ids: List of entry IDs to delete
    
    Returns:
        JSON string with deletion status
    """
    try:
        if not entry_ids:
            return json.dumps({'ok': False, 'error': 'entry_ids list is required'})
        
        memory_system = _get_or_create_memory_system(agent_id)
        
        memory_system.vector_store.rag.delete_chat_history(
            agent_ID=agent_id,
            ids=entry_ids
        )
        
        return json.dumps({
            'ok': True,
            'message': 'memories_deleted',
            'agent_id': agent_id,
            'deleted_count': len(entry_ids),
            'entry_ids': entry_ids
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


@mcp.tool()
async def list_all_memories(agent_id: str, limit: int = 50) -> str:
    """
    List all memory entries for an agent.
    
    Args:
        agent_id: Unique identifier for the agent
        limit: Maximum number of entries to return (default: 50)
    
    Returns:
        JSON string with list of all memory entries
    """
    try:
        memory_system = _get_or_create_memory_system(agent_id)
        
        memories = memory_system.get_all_memories()
        
        results = []
        for mem in memories[:limit]:
            results.append({
                'entry_id': mem.entry_id,
                'lossless_restatement': mem.lossless_restatement,
                'keywords': mem.keywords,
                'timestamp': mem.timestamp,
                'location': mem.location,
                'persons': mem.persons,
                'entities': mem.entities,
                'topic': mem.topic
            })
        
        return json.dumps({
            'ok': True,
            'agent_id': agent_id,
            'total_memories': len(memories),
            'returned': len(results),
            'memories': results
        })
    except Exception as e:
        return json.dumps({'ok': False, 'error': str(e)})


# ============================================================================
# MCP RESOURCES - Expose data sources for Claude to read
# ============================================================================

@mcp.resource("memory://agents/list")
async def list_active_agents() -> str:
    """List all agents with active memory systems."""
    return json.dumps({
        'active_agents': list(_memory_systems_cache.keys()),
        'count': len(_memory_systems_cache)
    })


@mcp.resource("memory://config/info")
async def get_server_info() -> str:
    """Get information about the MCP Memory Server."""
    return json.dumps({
        'name': 'Manhattan Memory MCP Server',
        'version': '1.0.0',
        'description': 'MCP server for Memory CRUD operations using SimpleMem and ChromaDB',
        'available_tools': [
            'create_memory',
            'process_raw_dialogues',
            'add_memory_direct',
            'search_memory',
            'get_context_answer',
            'update_memory_entry',
            'delete_memory_entries',
            'list_all_memories'
        ]
    })


# ============================================================================
# Main entry point
# ============================================================================

def main():
    """Initialize and run the MCP server."""
    print("Starting Manhattan Memory MCP Server...")
    print("Tools available: create_memory, process_raw_dialogues, add_memory_direct,")
    print("                 search_memory, get_context_answer, update_memory_entry,")
    print("                 delete_memory_entries, list_all_memories")
    print("\nRunning on stdio transport...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
