#!/usr/bin/env python3
"""Test script for Manhattan Memory API"""

import httpx
import json

API_URL = 'https://www.themanhattanproject.ai'
API_KEY = 'sk-tg5T-vIyYnuprwVPcgoHGfX37HBsfPwAvHkV3WFyhkE'

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
}

def test_api():
    print("=" * 60)
    print("Testing Manhattan Memory API")
    print("=" * 60)
    
    # Step 1: Create memory system
    print("\n1. Creating memory system for agent 'mcp-test-agent'...")
    try:
        resp = httpx.post(
            f'{API_URL}/create_memory', 
            json={'agent_id': 'mcp-test-agent', 'clear_db': True},
            headers=headers,
            timeout=120.0
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text[:500]}")
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # Step 2: Add memory directly
    print("\n2. Adding memories directly...")
    memories = [
        {
            "lossless_restatement": "The Agent Architects Studio project was created by Dhruv in January 2025 to provide AI memory management APIs.",
            "keywords": ["Agent Architects", "Dhruv", "AI", "memory", "API"],
            "persons": ["Dhruv"],
            "topic": "project overview"
        },
        {
            "lossless_restatement": "The MCP server allows Claude Desktop, Cursor, and other AI coding agents to store and retrieve persistent memories.",
            "keywords": ["MCP", "Claude", "Cursor", "memory", "AI agents"],
            "entities": ["Claude Desktop", "Cursor", "MCP"],
            "topic": "MCP integration"
        },
        {
            "lossless_restatement": "The project uses ChromaDB for vector storage and supports hybrid search combining semantic and keyword matching.",
            "keywords": ["ChromaDB", "vector", "hybrid search", "semantic"],
            "entities": ["ChromaDB"],
            "topic": "technical architecture"
        }
    ]
    
    try:
        resp = httpx.post(
            f'{API_URL}/add_memory', 
            json={'agent_id': 'mcp-test-agent', 'memories': memories},
            headers=headers,
            timeout=120.0
        )
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text[:500]}")
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # Step 3: Search memories
    print("\n3. Searching memories for 'MCP server'...")
    try:
        resp = httpx.post(
            f'{API_URL}/read_memory', 
            json={'agent_id': 'mcp-test-agent', 'query': 'What is the MCP server?', 'top_k': 3},
            headers=headers,
            timeout=120.0
        )
        print(f"   Status: {resp.status_code}")
        result = resp.json()
        print(f"   Found {result.get('results_count', 0)} results")
        for r in result.get('results', [])[:2]:
            print(f"   - {r.get('lossless_restatement', '')[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_api()
