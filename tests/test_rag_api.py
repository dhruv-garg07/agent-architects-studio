#!/usr/bin/env python3
"""
Base-Level API Test for Document Ingestion and Retrieval.
Tests the /add_document and /search_documents endpoints.
"""

import requests
import json
import uuid
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = "http://127.0.0.1:1078"
API_KEY = os.getenv("MANHATTAN_API_KEY_TEST")
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def test_add_document(agent_id: str):
    print("\n" + "="*70)
    print("TEST: Ingesting Documents (/add_document)")
    print("="*70)
    
    url = f"{API_URL}/add_document"
    payload = {
        "agent_id": agent_id,
        "documents": [
            "Agent-Architects Studio is a powerful platform for orchestrating AI agents.",
            "The Manhattan API serves as the primary interface for agent operations.",
            "Retrieval-Augmented Generation (RAG) combines semantic search with LLM synthesis."
        ],
        "ids": [
            f"doc_test_{uuid.uuid4().hex[:8]}",
            f"doc_test_{uuid.uuid4().hex[:8]}",
            f"doc_test_{uuid.uuid4().hex[:8]}"
        ],
        "metadata": {
            "source": "api_test",
            "type": "documentation"
        },
        "chunking_mode": "fast"
    }
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Documents ingested successfully! Chunks created: {data.get('chunks_count')}")
            return True
        else:
            print(f"⚠️ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_search_documents(agent_id: str):
    print("\n" + "="*70)
    print("TEST: Searching Documents (/search_documents)")
    print("="*70)
    
    url = f"{API_URL}/search_documents"
    payload = {
        "agent_id": agent_id,
        "query": "What is Agent-Architects Studio?",
        "top_k": 2
    }
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Documents retrieved successfully!")
            print(f"Synthesized Answer:\n{data.get('synthesized_answer')}")
            print("\nRaw Reranked Results:")
            for i, res in enumerate(data.get('results', [])):
                print(f"  [{i+1}] {res.get('text')}")
            return True
        else:
            print(f"⚠️ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def run_tests():
    agent_id = "test-agent-" + uuid.uuid4().hex[:6]
    print(f"Using ephemeral Agent ID for docs test: {agent_id}")
    
    if test_add_document(agent_id):
        test_search_documents(agent_id)

if __name__ == "__main__":
    run_tests()
