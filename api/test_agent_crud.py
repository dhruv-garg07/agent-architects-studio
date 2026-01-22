#!/usr/bin/env python3
"""
Test script for Agent CRUD operations in mcp_memory_client.py

This script tests the agent CRUD wrapper functions directly without running the MCP server.
"""

import os
import sys
import json
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import HTTP client
try:
    import httpx
except ImportError:
    print("ERROR: httpx package not installed!")
    print("Install with: pip install httpx")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_API_URL = "https://www.themanhattanproject.ai"
API_URL = os.getenv("MANHATTAN_API_URL", DEFAULT_API_URL)
API_KEY = os.getenv("MANHATTAN_API_KEY", "sk-tg5T-vIyYnuprwVPcgoHGfX37HBsfPwAvHkV3WFyhkE")
REQUEST_TIMEOUT = 120.0


# ============================================================================
# HTTP Client Helpers
# ============================================================================

async def call_api(endpoint: str, payload: dict) -> dict:
    """Make an authenticated POST request to the Manhattan API."""
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


# ============================================================================
# Test Functions
# ============================================================================

async def test_list_agents():
    """Test listing all agents for the user."""
    print("\n" + "=" * 60)
    print("TEST: list_agents")
    print("=" * 60)
    
    result = await call_api_get("list_agents")
    print(json.dumps(result, indent=2))
    return result


async def test_create_agent():
    """Test creating a new agent."""
    print("\n" + "=" * 60)
    print("TEST: create_agent")
    print("=" * 60)
    
    payload = {
        "agent_name": "Test Agent",
        "agent_slug": "test-agent-crud",
        "permissions": {"chat": True, "memory": True},
        "limits": {"requests_per_day": 100},
        "description": "A test agent created via CRUD wrapper test"
    }
    
    result = await call_api("create_agent", payload)
    print(json.dumps(result, indent=2))
    return result


async def test_get_agent(agent_id: str):
    """Test getting a specific agent by ID."""
    print("\n" + "=" * 60)
    print(f"TEST: get_agent (agent_id: {agent_id})")
    print("=" * 60)
    
    result = await call_api("get_agent", {"agent_id": agent_id})
    print(json.dumps(result, indent=2))
    return result


async def test_update_agent(agent_id: str):
    """Test updating an agent."""
    print("\n" + "=" * 60)
    print(f"TEST: update_agent (agent_id: {agent_id})")
    print("=" * 60)
    
    payload = {
        "agent_id": agent_id,
        "updates": {
            "description": "Updated description via CRUD wrapper test",
            "metadata": {"updated_at_test": "2025-01-23"}
        }
    }
    
    result = await call_api("update_agent", payload)
    print(json.dumps(result, indent=2))
    return result


async def test_disable_agent(agent_id: str):
    """Test disabling (soft delete) an agent."""
    print("\n" + "=" * 60)
    print(f"TEST: disable_agent (agent_id: {agent_id})")
    print("=" * 60)
    
    result = await call_api("disable_agent", {"agent_id": agent_id})
    print(json.dumps(result, indent=2))
    return result


async def test_enable_agent(agent_id: str):
    """Test enabling a disabled agent."""
    print("\n" + "=" * 60)
    print(f"TEST: enable_agent (agent_id: {agent_id})")
    print("=" * 60)
    
    result = await call_api("enable_agent", {"agent_id": agent_id})
    print(json.dumps(result, indent=2))
    return result


async def test_delete_agent(agent_id: str):
    """Test permanently deleting an agent."""
    print("\n" + "=" * 60)
    print(f"TEST: delete_agent (agent_id: {agent_id})")
    print("=" * 60)
    
    result = await call_api("delete_agent", {"agent_id": agent_id})
    print(json.dumps(result, indent=2))
    return result


async def run_all_tests():
    """Run all agent CRUD tests."""
    print("=" * 60)
    print("  Agent CRUD Operations Test Suite")
    print("=" * 60)
    print(f"  API URL: {API_URL}")
    print(f"  API Key: {'✓ Configured' if API_KEY else '✗ Not set'}")
    print("=" * 60)
    
    # 1. List existing agents
    await test_list_agents()
    
    # 2. Create a new agent
    create_result = await test_create_agent()
    
    # Extract agent_id from result
    agent_id = None
    if isinstance(create_result, dict):
        agent_id = create_result.get('agent_id') or create_result.get('id')
    
    if not agent_id:
        print("\n⚠️ Could not extract agent_id from create response. Skipping remaining tests.")
        return
    
    print(f"\n✓ Created agent with ID: {agent_id}")
    
    # 3. Get the agent
    await test_get_agent(agent_id)
    
    # 4. Update the agent
    await test_update_agent(agent_id)
    
    # 5. Disable the agent
    await test_disable_agent(agent_id)
    
    # 6. Enable the agent
    await test_enable_agent(agent_id)
    
    # 7. Delete the agent (cleanup)
    await test_delete_agent(agent_id)
    
    print("\n" + "=" * 60)
    print("  All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
