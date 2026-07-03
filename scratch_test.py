import sys
import os
import uuid

# Setup paths to ensure imports from api and lib work
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'api'))
sys.path.insert(0, os.path.join(project_root, 'lib'))

from api.index import app

API_KEY = "sk-test-123"

def run_tests():
    print("Initializing Flask test client...")
    client = app.test_client()

    print("\n--- 1. Creating Agent via Manhattan API ---")
    agent_payload = {
        "api_key": API_KEY,
        "agent_name": "Manhattan API Test Agent",
        "agent_slug": f"api-test-{uuid.uuid4().hex[:8]}",
        "system_prompt": "You are a test agent."
    }
    
    resp = client.post("/create_agent", json=agent_payload)
    if resp.status_code != 201:
        print(f"Failed to create agent: {resp.status_code} - {resp.get_data(as_text=True)}")
        sys.exit(1)
        
    data = resp.get_json()
    agent_id = data.get('agent_id') or data.get('id')
    print(f"[OK] Agent created successfully! Agent ID: {agent_id}\n")
    

    print("--- 2. Pushing Documents via Manhattan API ---")
    doc1 = (
        "Volume 1: The architecture of the Manhattan system focuses heavily on decoupled memory.\n"
        "Agents are assigned isolated vector storage in ChromaDB to prevent leakage.\n" * 5
    )
    doc2 = (
        "Volume 2: SimpleMem is the cognitive framework that routes data.\n"
        "It categorizes memory into episodic, semantic, and procedural types.\n" * 5
    )
    
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    doc_payload = {
        "api_key": API_KEY,
        "agent_id": agent_id,
        "documents": [doc1, doc2],
        "ids": [doc1_id, doc2_id],
        "metadata": {"source": "API testing script"},
        "chunking_mode": "fast"
    }

    resp = client.post("/add_document", json=doc_payload)
    if resp.status_code != 200:
        print(f"Failed to add documents: {resp.status_code} - {resp.get_data(as_text=True)}")
        sys.exit(1)

    print("[OK] Documents uploaded and chunked successfully!\n")
    

    print("--- 3. Searching/Retrieving Documents via Manhattan API ---")
    search_payload = {
        "api_key": API_KEY,
        "agent_id": agent_id,
        "query": "What is the cognitive framework that routes data?",
        "top_k": 3
    }
    
    resp = client.post("/search_documents", json=search_payload)
    if resp.status_code != 200:
        print(f"Failed to search documents: {resp.status_code} - {resp.get_data(as_text=True)}")
        sys.exit(1)
        
    search_data = resp.get_json()
    chunks = search_data.get('results', [])
    synth = search_data.get('synthesized_answer', '')
    
    print(f"[OK] Found {len(chunks)} relevant chunks!")
    if chunks:
        print("\nTop Chunk Retrieved:")
        print(f"Text: {chunks[0].get('text', '')[:100]}...")
        print(f"Metadata: {chunks[0].get('metadata')}")
    
    print(f"\n[OK] Synthesized Answer from SimpleMem LLM:")
    print(f"> {synth}")
    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    run_tests()
