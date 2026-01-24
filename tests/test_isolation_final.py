"""
Test to verify agent_id isolation in print_memories
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))

from SimpleMem.main import create_system

# Create fresh system
print("\n[INIT] Creating fresh system...")
system = create_system(clear_db=True)

# Add ONLY to test_agent_1
print("\n[STEP 1] Adding dialogue ONLY to test_agent_1...")
system.vector_store.agent_id = "test_agent_1"
system.add_dialogue("Alice", "Bob, let's meet at Starbucks tomorrow")

# Verify agent_id is still test_agent_1
print(f"\n[CHECK] Current agent_id: {system.vector_store.agent_id}")

# Print memories of test_agent_1
print("\n[PRINT] Getting all entries from test_agent_1:")
system.print_memories()

# Now add to a DIFFERENT agent
print("\n\n[STEP 2] Adding dialogue to test_agent_2...")
system.vector_store.agent_id = "test_agent_2"
system.add_dialogue("Bob", "Okay, I'll prepare the materials")

# Switch BACK to test_agent_1 and print
print("\n[STEP 3] Switching back to test_agent_1 and printing memories...")
system.vector_store.agent_id = "test_agent_1"
print(f"[CHECK] Current agent_id: {system.vector_store.agent_id}")

print("\n[PRINT] Getting all entries from test_agent_1 (should NOT include Bob's prepare materials):")
system.print_memories()

# Get the raw entries to debug
print("\n[DEBUG] Raw entries from test_agent_1 collection:")
entries = system.get_all_memories()
print(f"Total entries: {len(entries)}")
for i, entry in enumerate(entries, 1):
    print(f"  [{i}] {entry.lossless_restatement[:70]} | Persons: {entry.persons}")
