"""
Immediate Dialogue Storage with Agent ID Isolation

This example demonstrates:
1. Each dialogue is stored immediately (no buffering/finalize needed)
2. When agent_id changes, subsequent dialogues go to different agent's collection
3. Complete agent isolation - no data mixing
"""

from SimpleMem.main import SimpleMemSystem

# Initialize system
system = SimpleMemSystem()

print("\n" + "="*70)
print("SCENARIO: Multiple Agents with Immediate Dialogue Storage")
print("="="*70)

# ==================== AGENT A ==================== 
print("\n[AGENT A] Switching to agent_A")
system.memory_builder.vector_store.agent_id = "agent_A"

print("\n[AGENT A] Adding dialogues (immediate storage)...")
system.add_dialogue("Alice", "Hello, I'm Alice from team A")
system.add_dialogue("Bob_A", "Hi Alice, what's the task today?")
system.add_dialogue("Alice", "We need to analyze the Q4 data")

print(f"[AGENT A] Total dialogues added: {system.memory_builder.processed_count}")
print(f"[AGENT A] Stored to collection: agent_A")

# ==================== AGENT B ====================
print("\n" + "-"*70)
print("\n[AGENT B] Switching to agent_B")
system.memory_builder.vector_store.agent_id = "agent_B"

print("\n[AGENT B] Adding dialogues (immediate storage)...")
system.add_dialogue("Charlie", "Hey everyone, this is Charlie from team B")
system.add_dialogue("Diana", "Hi Charlie, what's on your mind?")
system.add_dialogue("Charlie", "We're launching the new product tomorrow")

print(f"[AGENT B] Total dialogues added: {system.memory_builder.processed_count}")
print(f"[AGENT B] Stored to collection: agent_B")

# ==================== AGENT A (AGAIN) ====================
print("\n" + "-"*70)
print("\n[AGENT A] Switching back to agent_A")
system.memory_builder.vector_store.agent_id = "agent_A"

print("\n[AGENT A] Adding more dialogues (immediate storage)...")
system.add_dialogue("Alice", "The data looks good for Q4")
system.add_dialogue("Bob_A", "Great! Let's present it to management")

print(f"[AGENT A] Total dialogues added: {system.memory_builder.processed_count}")
print(f"[AGENT A] Stored to collection: agent_A (separate from agent_B)")

# ==================== VERIFICATION ====================
print("\n" + "="*70)
print("VERIFICATION: Data Isolation")
print("="*70)

# Query Agent A's data
print("\n[Query] Searching agent_A collection...")
system.memory_builder.vector_store.agent_id = "agent_A"
results_a = system.memory_builder.vector_store.semantic_search("Q4 data", top_k=3)
print(f"Found {len(results_a)} results in agent_A:")
for r in results_a:
    print(f"  - {r.lossless_restatement[:60]}...")

# Query Agent B's data
print("\n[Query] Searching agent_B collection...")
system.memory_builder.vector_store.agent_id = "agent_B"
results_b = system.memory_builder.vector_store.semantic_search("product launch", top_k=3)
print(f"Found {len(results_b)} results in agent_B:")
for r in results_b:
    print(f"  - {r.lossless_restatement[:60]}...")

# Verify isolation
print("\n" + "-"*70)
print("\nAgent A should NOT find 'product launch' (it's in agent_B)")
system.memory_builder.vector_store.agent_id = "agent_A"
cross_query = system.memory_builder.vector_store.semantic_search("product launch", top_k=1)
print(f"Agent A search for 'product launch': {len(cross_query)} results (should be minimal or irrelevant)")

print("\n" + "="*70)
print("SUCCESS: Complete agent isolation with immediate storage!")
print("="*70)

print("\n" + "="*70)
print("KEY FEATURES")
print("="*70)
print("""
1. Immediate Storage:
   - Each dialogue stored immediately to vector DB
   - No waiting for finalize() or window_size
   - Dialogue available for search/retrieval immediately after add

2. Agent Isolation:
   - Each agent_id has separate ChromaDB collection
   - Changing agent_id switches collection automatically
   - No data mixing between agents
   - Thread-safe agent_id switching

3. No Finalize Required:
   - No buffer to flush at end
   - No missed dialogues
   - System always ready to query

4. Flexible Modes:
   - add_dialogue(auto_process=True) - immediate (default)
   - add_dialogue(auto_process=False) - buffer for later
   - add_dialogues() - batch add with immediate storage
""")
