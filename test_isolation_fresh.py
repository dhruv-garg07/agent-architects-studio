"""
Fresh isolation test - verify exact state of collections
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, './SimpleMem')

from SimpleMem.main import create_system

# Create FRESH system
print("\n[INIT] Creating fresh system with empty DB...")
system = create_system(clear_db=True)
vector_store = system.memory_builder.vector_store
client = vector_store.agentic_RAG.wrapper.manager.client

# Verify empty state
print("\nCollections AFTER clearing:")
all_collections = client.list_collections()
for col in all_collections:
    if col.count() > 0:
        print(f"  - {col.name}: {col.count()} documents")

# Add ONE dialogue to test_agent_1
print("\n[ADD STEP 1] Adding single dialogue to test_agent_1...")
vector_store.agent_id = "test_agent_1"
system.add_dialogue("Alice", "Bob, let's meet at Starbucks tomorrow")

print("\nCollections AFTER adding to test_agent_1:")
all_collections = client.list_collections()
for col in all_collections:
    if col.name in ["test_agent_1", "test_agent_2"]:
        print(f"  - {col.name}: {col.count()} documents")

#Add ONE dialogue to test_agent_2
print("\n[ADD STEP 2] Adding single dialogue to test_agent_2...")
vector_store.agent_id = "test_agent_2"
system.add_dialogue("Bob", "Okay, I'll prepare materials")

print("\nCollections AFTER adding to test_agent_2:")
all_collections = client.list_collections()
for col in all_collections:
    if col.name in ["test_agent_1", "test_agent_2"]:
        print(f"  - {col.name}: {col.count()} documents")
        # Show document IDs
        all_docs = col.get()
        print(f"    Document IDs: {all_docs['ids']}")

# Check for cross-contamination
print("\n[TEST] Searching test_agent_1 for 'Bob' (should NOT find Bob's entry)...")
vector_store.agent_id = "test_agent_1"
results = vector_store.semantic_search("Bob", top_k=10)
print(f"Found {len(results)} results:")
for r in results:
    print(f"  - {r.lossless_restatement[:80]}")

print("\n[TEST] Searching test_agent_2 for 'Alice' (should NOT find Alice's entry)...")
vector_store.agent_id = "test_agent_2"
results = vector_store.semantic_search("Alice", top_k=10)
print(f"Found {len(results)} results:")
for r in results:
    print(f"  - {r.lossless_restatement[:80]}")
