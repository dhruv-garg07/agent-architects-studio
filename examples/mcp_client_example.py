#!/usr/bin/env python3
"""
MCP Socket.IO Client Example

This example shows how to connect to the Manhattan MCP server via Socket.IO
and use the memory tools remotely.

No client files are needed - just connect via WebSocket!

Requirements:
    pip install python-socketio[client]

Usage:
    python mcp_client_example.py

Environment Variables:
    MCP_URL - Server URL (default: https://themanhattanproject.ai)
    MCP_API_KEY - Your API key
"""

import os
import socketio
import json
from typing import Any, Dict, Optional

# Configuration
MCP_URL = os.getenv("MCP_URL", "https://themanhattanproject.ai")
MCP_API_KEY = os.getenv("MCP_API_KEY", "")

# Create Socket.IO client
sio = socketio.Client()


@sio.event(namespace='/mcp')
def connect():
    print(f"✅ Connected to MCP server at {MCP_URL}")


@sio.event(namespace='/mcp')
def disconnect():
    print("❌ Disconnected from MCP server")


@sio.on('connection_established', namespace='/mcp')
def on_connection_established(data):
    print(f"🔗 Session established: {data.get('client_id')}")


def get_tools(api_key: str) -> Dict[str, Any]:
    """Get list of available MCP tools."""
    result = sio.call(
        "mcp:get_tools",
        {"api_key": api_key},
        namespace="/mcp",
        timeout=30
    )
    return result


def call_tool(api_key: str, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
    """Execute an MCP tool."""
    result = sio.call(
        "mcp:call_tool",
        {
            "api_key": api_key,
            "tool": tool_name,
            "arguments": arguments or {}
        },
        namespace="/mcp",
        timeout=60
    )
    return result


def get_instructions(api_key: str) -> Dict[str, Any]:
    """Get MCP usage instructions."""
    result = sio.call(
        "mcp:get_instructions",
        {"api_key": api_key},
        namespace="/mcp",
        timeout=10
    )
    return result


def main():
    """Main example demonstrating MCP usage."""
    
    api_key = MCP_API_KEY
    if not api_key:
        print("⚠️  No API key set. Set MCP_API_KEY environment variable.")
        print("    Using development mode with 'sk-test-key'")
        api_key = "sk-test-key"
    
    print(f"\n🚀 Connecting to Manhattan MCP Server...")
    print(f"   URL: {MCP_URL}")
    
    try:
        # Connect to the server
        sio.connect(MCP_URL, namespaces=["/mcp"])
        
        print("\n📋 Getting available tools...")
        tools = get_tools(api_key)
        
        if tools.get("ok"):
            print(f"   Found {tools.get('tool_count', 0)} tools:")
            for name in list(tools.get("tools", {}).keys())[:5]:
                print(f"   - {name}")
            if len(tools.get("tools", {})) > 5:
                print(f"   ... and {len(tools.get('tools', {})) - 5} more")
        else:
            print(f"   Error: {tools.get('error')}")
            return
        
        print("\n🧠 Testing memory search...")
        result = call_tool(api_key, "search_memory", {
            "agent_id": "84aab1f8-3ea9-4c6a-aa3c-cd8eaa274a5e",
            "query": "user preferences",
            "top_k": 3
        })
        
        if isinstance(result, dict):
            if result.get("ok"):
                print(f"   Found {result.get('results_count', 0)} memories")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"   Result: {result}")
        
        print("\n💾 Testing auto_remember...")
        result = call_tool(api_key, "auto_remember", {
            "agent_id": "84aab1f8-3ea9-4c6a-aa3c-cd8eaa274a5e",
            "user_message": "My name is Test User and I like Python programming"
        })
        
        if isinstance(result, dict) and result.get("ok"):
            print("   Memory stored successfully!")
        else:
            error = result.get("error") if isinstance(result, dict) else str(result)
            print(f"   Result: {error}")
        
        print("\n📖 Getting instructions...")
        instructions = get_instructions(api_key)
        if instructions.get("ok"):
            print("   Instructions retrieved successfully!")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        if sio.connected:
            sio.disconnect()


if __name__ == "__main__":
    main()
