"""
Demo script for GitMem.
This script demonstrates how to:
1. Initialize the memory store (indirectly via API)
2. Add memories for an agent
3. Query memories
4. Commit the state
"""

import sys
import os
import time

# Add root to path so we can import gitmem if running locally without install
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# For this demo, we can either use the SDK (requires server running) 
# OR use the internal classes directly for instant verification without valid server.
# Let's use internal classes for the "Verification" step to ensure it works immediately for the user.
from gitmem.core.memory_store import MemoryStore
from gitmem.core.models import MemoryItem

def run_demo():
    print("--- GITMEM INTERNAL DEMO ---")
    store = MemoryStore()
    
    agent_id = "agent_007"
    
    # 1. Add Memories
    print(f"\n[1] Adding memories for {agent_id}...")
    m1 = MemoryItem(agent_id=agent_id, type="episodic", content="The user prefers dark mode.", metadata={"source": "chat"})
    m2 = MemoryItem(agent_id=agent_id, type="episodic", content="Project deadline is Friday.", metadata={"priority": "high"})
    
    id1 = store.add_memory(m1)
    id2 = store.add_memory(m2)
    print(f"Stored memories: {id1}, {id2}")
    
    # 2. List Memories
    print(f"\n[2] Listing memories for {agent_id}...")
    memories = store.list_memories(agent_id, "episodic")
    for m in memories:
        print(f" - [{m.created_at}] {m.content}")
        
    # 3. Commit
    print(f"\n[3] Committing state...")
    commit = store.commit_state(agent_id, "Initial memory sync")
    print(f"Committed: {commit.hash} - {commit.message}")
    
    print("\n--- DEMO COMPLETE ---")
    print("Data stored in ./gitmem_data/")

if __name__ == "__main__":
    run_demo()
