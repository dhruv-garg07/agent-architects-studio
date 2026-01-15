"""
Test to verify that agent_id isolation prevents cross-agent data mixing
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, './SimpleMem')

from SimpleMem.main import create_system
from SimpleMem.models.memory_entry import Dialogue

def test_agent_isolation():
    """Verify complete agent isolation in vector store"""
    
    print("\n" + "="*60)
    print("TESTING AGENT_ID ISOLATION IN VECTOR STORE")
    print("="*60)
    
    # Create system
    system = create_system(clear_db=True)
    vector_store = system.memory_builder.vector_store
    
    # Add dialogue to test_agent_1
    print("\n[STEP 1] Adding dialogue to test_agent_1...")
    vector_store.agent_id = "test_agent_1"
    system.add_dialogue("Alice", "Bob, let's meet at Starbucks tomorrow at 2pm to discuss the new product", "2025-11-15T14:30:00")
    
    # Verify in test_agent_1 collection
    print("\n[VERIFY] Searching test_agent_1 collection for 'Alice'...")
    vector_store.agent_id = "test_agent_1"
    results_agent1_search1 = vector_store.semantic_search("Alice", top_k=10)
    print(f"Found {len(results_agent1_search1)} results in test_agent_1: {[r.lossless_restatement[:50] for r in results_agent1_search1]}")
    
    # Add dialogue to test_agent_2
    print("\n[STEP 2] Adding dialogue to test_agent_2...")
    vector_store.agent_id = "test_agent_2"
    system.add_dialogue("Bob", "Okay, I'll prepare the materials", "2025-11-15T14:31:00")
    
    # Verify in test_agent_2 collection
    print("\n[VERIFY] Searching test_agent_2 collection for 'Bob'...")
    vector_store.agent_id = "test_agent_2"
    results_agent2_search = vector_store.semantic_search("Bob", top_k=10)
    print(f"Found {len(results_agent2_search)} results in test_agent_2: {[r.lossless_restatement[:50] for r in results_agent2_search]}")
    
    # Back to test_agent_1 - check for contamination
    print("\n[CRITICAL CHECK] Back to test_agent_1 - searching for 'Bob' (should find NOTHING)...")
    vector_store.agent_id = "test_agent_1"
    results_contamination = vector_store.semantic_search("Bob", top_k=10)
    
    if results_contamination:
        print(f"[FAIL] CONTAMINATION DETECTED! Found {len(results_contamination)} results:")
        for r in results_contamination:
            print(f"  - {r.lossless_restatement[:60]}")
        return False
    else:
        print(f"[PASS] NO CONTAMINATION! test_agent_1 correctly isolated from test_agent_2")
    
    # Check what's actually in each collection
    print("\n[DEBUG] Checking ChromaDB collections directly...")
    
    # Get collection info
    vector_store.agent_id = "test_agent_1"
    try:
        collection_1 = vector_store.agentic_RAG.wrapper.manager.get_collection("test_agent_1")
        count_1 = collection_1.count()
        print(f"test_agent_1 collection has {count_1} documents")
    except Exception as e:
        print(f"Error checking test_agent_1 collection: {e}")
    
    vector_store.agent_id = "test_agent_2"
    try:
        collection_2 = vector_store.agentic_RAG.wrapper.manager.get_collection("test_agent_2")
        count_2 = collection_2.count()
        print(f"test_agent_2 collection has {count_2} documents")
    except Exception as e:
        print(f"Error checking test_agent_2 collection: {e}")
    
    # Test retrieval isolation
    print("\n[FINAL TEST] Verify retrieval doesn't mix agents...")
    vector_store.agent_id = "test_agent_1"
    all_entries_1 = vector_store.semantic_search("", top_k=100)  # Get all
    print(f"test_agent_1 total entries: {len(all_entries_1)}")
    for entry in all_entries_1:
        print(f"  - {entry.lossless_restatement[:60]}")
    
    vector_store.agent_id = "test_agent_2"
    all_entries_2 = vector_store.semantic_search("", top_k=100)  # Get all
    print(f"test_agent_2 total entries: {len(all_entries_2)}")
    for entry in all_entries_2:
        print(f"  - {entry.lossless_restatement[:60]}")
    
    # Check for any overlap
    print("\n[CHECK] Looking for overlapping entries...")
    set_1 = set(e.entry_id for e in all_entries_1)
    set_2 = set(e.entry_id for e in all_entries_2)
    overlap = set_1.intersection(set_2)
    
    if overlap:
        print(f"[FAIL] OVERLAP DETECTED! {len(overlap)} shared entries:")
        for eid in overlap:
            print(f"  - {eid}")
        return False
    else:
        print(f"[PASS] NO OVERLAP! Collections are properly isolated")
    
    print("\n" + "="*60)
    print("ISOLATION TEST COMPLETE")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_agent_isolation()
    sys.exit(0 if success else 1)
