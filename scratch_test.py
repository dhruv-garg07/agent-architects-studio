import requests
import uuid

API_BASE = "http://localhost:5000/api"
API_KEY = "test_key"  # Assuming some test key or bypassing it for local tests
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def test_ingest_and_retrieve():
    agent_id = f"test-ingest-agent-{uuid.uuid4().hex[:8]}"
    print(f"Testing with Agent ID: {agent_id}")
    
    # 1. Ingest document
    print("\n--- Ingesting Documents ---")
    docs = [
        "The quick brown fox jumps over the lazy dog. This is a classic pangram.",
        "Agent Architects Studio provides advanced multi-agent orchestrations for complex workflows.",
        "Retrieval Augmented Generation (RAG) is a critical component of modern LLM systems."
    ]
    ids = ["doc1", "doc2", "doc3"]
    
    ingest_payload = {
        "agent_id": agent_id,
        "documents": docs,
        "ids": ids,
        "metadata": {
            "source": "scratch_test",
            "filename": "test_docs.txt"
        }
    }
    
    try:
        res = requests.post(f"{API_BASE}/add_document", json=ingest_payload, headers=HEADERS)
        print(f"Ingest Response [{res.status_code}]: {res.text}")
    except Exception as e:
        print(f"Ingest Request Failed: {e}")
        return

    # 2. Retrieve document
    print("\n--- Retrieving Documents ---")
    retrieve_payload = {
        "agent_id": agent_id,
        "query": "What does Agent Architects Studio provide?"
    }
    
    try:
        res = requests.post(f"{API_BASE}/retrieve", json=retrieve_payload, headers=HEADERS)
        print(f"Retrieve Response [{res.status_code}]:")
        try:
            results = res.json()
            for r in results.get("results", []):
                print(f" - {r}")
        except:
            print(res.text)
    except Exception as e:
        print(f"Retrieve Request Failed: {e}")

if __name__ == "__main__":
    test_ingest_and_retrieve()
