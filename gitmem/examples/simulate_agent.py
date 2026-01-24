"""
GitMem Agent Simulation Script

This script simulates an AI agent interacting with the GitMem API.
It demonstrates all real-time features:
- Heartbeats (agent comes online)
- Memory addition (episodic, semantic)
- Commits (cognitive snapshots)
- Semantic facts (knowledge graph)
- Context queries

Run with: python simulate_agent.py <agent_id>
"""

import requests
import time
import sys
import random
from datetime import datetime

BASE_URL = "http://localhost:1078/gitmem/api"

# Sample memory contents for realistic simulation
SAMPLE_MEMORIES = [
    "User prefers concise responses without excessive explanation.",
    "User is building a GITMEM SDK for AI memory management.",
    "User works at Texas Instruments in the AI research division.",
    "User mentioned preference for Python over JavaScript.",
    "User asked about vector databases - specifically ChromaDB.",
    "User is interested in multi-agent collaboration patterns.",
    "User wants real-time UI updates for the dashboard.",
    "Project uses Flask backend with React frontend.",
]

SAMPLE_FACTS = [
    ("User", "works_at", "Texas Instruments"),
    ("GITMEM", "uses", "ChromaDB"),
    ("Dashboard", "supports", "WebSocket"),
    ("Agent", "stores", "EpisodicMemory"),
    ("User", "prefers", "Python"),
]

SAMPLE_QUERIES = [
    "What are the user's preferences?",
    "What is the user working on?",
    "What technologies are being used?",
    "What does the user prefer?",
]

def run_agent(agent_id, model="GPT-4"):
    print(f"🚀 Starting agent {agent_id} with model {model}...")
    print(f"📡 Connecting to {BASE_URL}")
    print("=" * 50)
    
    memory_count = 0
    commit_count = 0
    
    while True:
        try:
            # 1. Heartbeat - keeps agent online
            resp = requests.post(f"{BASE_URL}/agents/heartbeat", json={
                "agent_id": agent_id,
                "model": model
            })
            if resp.status_code == 200:
                data = resp.json()
                print(f"💓 [{agent_id}] Heartbeat OK • Active agents: {data.get('active_agents')}")
            else:
                print(f"❌ [{agent_id}] Heartbeat failed: {resp.text}")
            
            # 2. Add memory (30% chance per cycle)
            if random.random() < 0.4:
                content = random.choice(SAMPLE_MEMORIES)
                mem_type = random.choice(["episodic", "semantic"])
                importance = round(random.uniform(0.5, 1.0), 2)
                scope = random.choice(["private", "shared"])
                
                resp = requests.post(f"{BASE_URL}/memory", json={
                    "agent_id": agent_id,
                    "content": content,
                    "type": mem_type,
                    "importance": importance,
                    "scope": scope
                })
                
                if resp.status_code == 201:
                    memory_count += 1
                    print(f"🧠 [{agent_id}] Added {mem_type} memory #{memory_count}")
                    print(f"   └─ \"{content[:50]}...\" (importance: {importance})")
                else:
                    print(f"❌ Memory add failed: {resp.text}")
            
            # 3. Commit state periodically (after every 3 memories)
            if memory_count > 0 and memory_count % 3 == 0 and random.random() < 0.5:
                commit_count += 1
                message = f"Cognitive snapshot #{commit_count}: {memory_count} memories"
                
                resp = requests.post(f"{BASE_URL}/commit", json={
                    "agent_id": agent_id,
                    "message": message,
                    "author": agent_id
                })
                
                if resp.status_code == 201:
                    data = resp.json()
                    print(f"📝 [{agent_id}] Commit created: {data.get('commit_hash', 'unknown')[:7]}")
                    print(f"   └─ \"{message}\"")
                else:
                    print(f"❌ Commit failed: {resp.text}")
            
            # 4. Add semantic fact (20% chance)
            if random.random() < 0.2:
                subject, predicate, obj = random.choice(SAMPLE_FACTS)
                
                resp = requests.post(f"{BASE_URL}/semantic-fact", json={
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "agent_id": agent_id
                })
                
                if resp.status_code == 201:
                    print(f"🔗 [{agent_id}] Added fact: {subject} → {predicate} → {obj}")
                else:
                    print(f"❌ Semantic fact failed: {resp.text}")
            
            # 5. Context query (15% chance)
            if random.random() < 0.15:
                query = random.choice(SAMPLE_QUERIES)
                
                resp = requests.post(f"{BASE_URL}/context", json={
                    "query": query,
                    "agent_id": agent_id,
                    "max_tokens": 1000
                })
                
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"🔍 [{agent_id}] Context query: \"{query}\"")
                    print(f"   └─ Retrieved {data.get('memories_returned', 0)} memories ({data.get('tokens_used', 0)} tokens)")
                else:
                    print(f"❌ Context query failed: {resp.text}")
            
            # Wait before next cycle
            print("-" * 40)
            time.sleep(5)
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Agent {agent_id} shutting down...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("GitMem Agent Simulator")
        print("=" * 40)
        print("Usage: python simulate_agent.py <agent_id> [model]")
        print("")
        print("Examples:")
        print("  python simulate_agent.py agent-007")
        print("  python simulate_agent.py agent-007 GPT-5")
        print("  python simulate_agent.py claude-agent Claude-3")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "GPT-4"
    
    run_agent(agent_id, model)

