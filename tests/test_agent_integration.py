#!/usr/bin/env python3
"""
Test script to verify that agents created via MCP/API are visible in GitMem UI
and properly integrated with Supabase and ChromaDB.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_URL = "http://127.0.0.1:1078"
API_KEY = "sk-tg5T-vIyYnuprwVPcgoHGfX37HBsfPwAvHkV3WFyhkE"

def test_create_agent():
    """Test creating an agent via API"""
    print("\n" + "="*70)
    print("TEST 1: Creating 'Sharing agent 1' via Manhattan API")
    print("="*70)
    
    url = f"{API_URL}/create_agent"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "agent_name": "Sharing agent 1",
        "agent_slug": "sharing-agent-1",
        "permissions": {
            "chat": True,
            "memory": True,
            "read": True,
            "write": True
        },
        "limits": {
            "requests_per_day": 10000,
            "max_memory_items": 100000
        },
        "description": "An agent for sharing and collaboration - created via API test",
        "metadata": {
            "created_via": "test_script",
            "test_timestamp": datetime.now().isoformat()
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Agent created successfully!")
            print(json.dumps(data, indent=2))
            
            agent_id = data.get("agent_id")
            if agent_id:
                return agent_id
        else:
            print(f"\n⚠️  Response: {response.text}")
            # Check if agent already exists
            if "already exists" in response.text:
                print("\nAgent already exists, proceeding with existing agent...")
                return find_existing_agent()
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return None

def find_existing_agent():
    """Find the existing 'Sharing agent 1' agent"""
    print("\n" + "="*70)
    print("Finding existing 'Sharing agent 1' agent")
    print("="*70)
    
    url = f"{API_URL}/list_agents"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("agents"):
                for agent in data["agents"]:
                    if agent.get("agent_slug") == "sharing-agent-1":
                        print(f"✅ Found agent: {agent.get('agent_id')}")
                        return agent.get("agent_id")
    except Exception as e:
        print(f"❌ Error finding agent: {e}")
    
    return None

def test_add_memory(agent_id):
    """Test adding memories to the agent"""
    print("\n" + "="*70)
    print(f"TEST 2: Adding memories to agent {agent_id}")
    print("="*70)
    
    url = f"{API_URL}/add_memory"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    memories = [
        {
            "lossless_restatement": "This agent is designed for sharing knowledge and collaborating with other agents.",
            "keywords": ["sharing", "collaboration", "knowledge", "agent"],
            "topic": "agent purpose",
            "persons": [],
            "timestamp": datetime.now().isoformat()
        },
        {
            "lossless_restatement": f"The agent was created on {datetime.now().strftime('%B %d, %Y')} through the MCP server and Manhattan API.",
            "keywords": ["creation", "date", "MCP", "Manhattan API", "server"],
            "topic": "agent metadata",
            "persons": [],
            "timestamp": datetime.now().isoformat()
        },
        {
            "lossless_restatement": "This agent is part of the Agent Architects Studio project and uses GitMem for memory management with Supabase and ChromaDB integration.",
            "keywords": ["Agent Architects Studio", "GitMem", "memory management", "Supabase", "ChromaDB"],
            "topic": "project context",
            "persons": [],
            "timestamp": datetime.now().isoformat()
        },
        {
            "lossless_restatement": "The agent's primary capability is to store and recall shared information across different sessions with persistent memory.",
            "keywords": ["capability", "storage", "recall", "sessions", "persistent memory"],
            "topic": "agent capabilities",
            "persons": [],
            "timestamp": datetime.now().isoformat()
        },
        {
            "lossless_restatement": "Successfully integrated with Supabase for cloud persistence, ChromaDB for vector embeddings, and local filesystem for Git-like version control.",
            "keywords": ["integration", "Supabase", "ChromaDB", "vector", "version control"],
            "topic": "technical stack",
            "persons": [],
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    payload = {
        "agent_id": agent_id,
        "memories": memories
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Memories added successfully!")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"\n⚠️  Response: {response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return False

def test_verify_in_gitmem_ui(agent_id):
    """Verify the agent appears in GitMem UI"""
    print("\n" + "="*70)
    print("TEST 3: Verifying agent appears in GitMem UI")
    print("="*70)
    
    url = f"{API_URL}/gitmem/"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            html_content = response.text
            if "Sharing agent 1" in html_content or agent_id in html_content:
                print(f"\n✅ Agent visible in GitMem landing page!")
                return True
            else:
                print(f"\n⚠️  Agent not yet visible in GitMem UI")
                print("Checking API endpoint for agents...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # Check API endpoint
    try:
        api_url = f"{API_URL}/gitmem/api/stats"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"\nGitMem Stats: {json.dumps(data, indent=2)}")
    except:
        pass
    
    return False

def test_search_memory(agent_id):
    """Test searching memories"""
    print("\n" + "="*70)
    print(f"TEST 4: Searching memories for agent {agent_id}")
    print("="*70)
    
    url = f"{API_URL}/read_memory"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "agent_id": agent_id,
        "query": "agent capabilities and purpose",
        "top_k": 5
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Memory search successful!")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"\n⚠️  Response: {response.text}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return False

def main():
    print("\n" + "🚀"*35)
    print(" AGENT INTEGRATION TEST - MCP/API → GitMem UI")
    print("🚀"*35)
    print(f"\nAPI URL: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Create agent
    agent_id = test_create_agent()
    
    if not agent_id:
        print("\n❌ Failed to create or find agent. Aborting tests.")
        return
    
    print(f"\n✅ Using agent ID: {agent_id}")
    
    # Test 2: Add memories
    time.sleep(1)  # Small delay
    memory_success = test_add_memory(agent_id)
    
    # Test 3: Verify in GitMem UI
    time.sleep(1)  # Small delay
    ui_success = test_verify_in_gitmem_ui(agent_id)
    
    # Test 4: Search memories
    time.sleep(1)  # Small delay
    search_success = test_search_memory(agent_id)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✅ Agent Created: {agent_id is not None}")
    print(f"✅ Memories Added: {memory_success}")
    print(f"✅ Visible in GitMem UI: {ui_success}")
    print(f"✅ Memory Search Works: {search_success}")
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print(f"1. Open http://localhost:1078/gitmem/ in your browser")
    print(f"2. Look for 'Sharing agent 1' in the agent list")
    print(f"3. Click on it to view memories and context")
    print(f"4. Check Supabase table 'api_agents' for the agent record")
    print(f"5. Check ChromaDB collection for vector embeddings")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
