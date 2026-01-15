"""
Debug script to check ChromaDB collections and verify isolation
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, './SimpleMem')

from SimpleMem.main import create_system

# Create system
system = create_system(clear_db=True)
vector_store = system.memory_builder.vector_store

# Add some dialogues
print("\n[ADD] Dialogue to test_agent_1...")
vector_store.agent_id = "test_agent_1"
system.add_dialogue("Alice", "Bob, let's meet at Starbucks tomorrow")

print("\n[ADD] Dialogue to test_agent_2...")
vector_store.agent_id = "test_agent_2"
system.add_dialogue("Bob", "Okay, I'll prepare materials")

print("\n[DEBUG] Checking ChromaDB client...")
client = vector_store.agentic_RAG.wrapper.manager.client

# List all collections
print("\nAll collections in ChromaDB:")
try:
    all_collections = client.list_collections()
    for col in all_collections:
        print(f"  - {col.name}: {col.count()} documents")
        # Print document IDs
        print(f"    Documents:")
        try:
            data = col.get()
            for doc_id, content in zip(data['ids'], data['documents']):
                print(f"      - {doc_id}: {content[:60]}")
        except Exception as e:
            print(f"    Error getting documents: {e}")
except Exception as e:
    print(f"Error listing collections: {e}")

print("\n[VERIFY] Query test_agent_1 directly...")
try:
    col1 = client.get_or_create_collection("test_agent_1")
    print(f"test_agent_1 collection has {col1.count()} documents")
    # Get all documents
    all_docs_1 = col1.get()
    print(f"  IDs: {all_docs_1['ids']}")
    print(f"  Documents:")
    for doc_id, doc in zip(all_docs_1['ids'], all_docs_1['documents']):
        print(f"    - {doc_id}: {doc[:80]}")
    
    # Now query
    results = col1.query(query_texts=["Alice"], n_results=10)
    print(f"\nQuery 'Alice' returned {len(results['ids'][0])} results:")
    for doc in results['documents'][0]:
        print(f"  - {doc[:80]}")
except Exception as e:
    print(f"Error: {e}")

print("\n[VERIFY] Query test_agent_2 directly...")
try:
    col2 = client.get_or_create_collection("test_agent_2")
    print(f"test_agent_2 collection has {col2.count()} documents")
    # Get all documents
    all_docs_2 = col2.get()
    print(f"  IDs: {all_docs_2['ids']}")
    print(f"  Documents:")
    for doc_id, doc in zip(all_docs_2['ids'], all_docs_2['documents']):
        print(f"    - {doc_id}: {doc[:80]}")
    
    # Now query
    results = col2.query(query_texts=["Bob"], n_results=10)
    print(f"\nQuery 'Bob' returned {len(results['ids'][0])} results:")
    for doc in results['documents'][0]:
        print(f"  - {doc[:80]}")
except Exception as e:
    print(f"Error: {e}")
