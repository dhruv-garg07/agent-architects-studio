#!/usr/bin/env python3
"""
System Test for RAG Pipeline (High Complexity).
Simulates a complex real-world scenario with large document ingestion,
chat memory context, and complex multi-layered semantic retrieval.
"""

import requests
import json
import uuid
import time
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = "http://127.0.0.1:1078"
API_KEY = os.getenv("MANHATTAN_API_KEY_TEST")
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# Complex text source that requires chunking
COMPLEX_DOCUMENT = """
Quantum Computing Fundamentals:
Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve problems too complex for classical computers. 
Unlike classical bits which are 0 or 1, qubits can exist in a superposition of states. 
Entanglement allows qubits that are separated by incredible distances to interact with each other instantaneously.

Applications of Quantum Computing:
1. Cryptography: Shor's algorithm can factorize large prime numbers exponentially faster than known classical algorithms, threatening RSA.
2. Drug Discovery: Simulating molecular structures at the quantum level to discover new pharmaceuticals.
3. Financial Modeling: Optimizing portfolios using quantum annealing.

Challenges:
The biggest challenge is maintaining qubit stability, a problem known as quantum decoherence. Error correction in quantum computers requires thousands of physical qubits to create a single logical, stable qubit.
"""

def create_agent(agent_slug: str):
    print("\n" + "="*70)
    print(f"TEST: Creating System Test Agent: {agent_slug}")
    print("="*70)
    
    url = f"{API_URL}/create_agent"
    payload = {
        "agent_name": "System Test Agent",
        "agent_slug": agent_slug,
        "permissions": {"chat": True, "memory": True, "read": True, "write": True},
        "limits": {"requests_per_day": 1000},
        "system-prompt": "System test agent for high complexity RAG."
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code in [200, 201]:
        print("✅ Agent created.")
        return response.json().get("agent_id")
    elif "already exists" in response.text:
        print("✅ Agent exists, continuing.")
        return agent_slug
    else:
        print(f"⚠️ Agent creation failed: {response.text}")
        return agent_slug # Fallback to using slug as ID

def ingest_large_document(agent_id: str):
    print("\n" + "="*70)
    print("TEST: Ingesting Large Complex Document (Advanced Chunking)")
    print("="*70)
    
    url = f"{API_URL}/add_document"
    payload = {
        "agent_id": agent_id,
        "documents": [COMPLEX_DOCUMENT],
        "ids": [f"quantum_doc_{uuid.uuid4().hex[:8]}"],
        "metadata": {"topic": "quantum_physics", "security": "public"},
        "chunking_mode": "advanced" # Forces semantic/advanced chunker if available
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"✅ Document ingested. Response: {response.json()}")
        return True
    else:
        print(f"⚠️ Failed to ingest: {response.text}")
        return False

def add_chat_context(agent_id: str):
    print("\n" + "="*70)
    print("TEST: Adding Contextual Chat History (SimpleMem)")
    print("="*70)
    
    url = f"{API_URL}/add_memory"
    payload = {
        "agent_id": agent_id,
        "session_id": "test_session_1",
        "memories": [{"lossless_restatement": "User asked about the primary challenges of scaling quantum computers yesterday. We noted it was decoherence."}],
        "metadata": {"type": "chat_summary"}
    }
    
    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        if response.status_code == 200:
            print("✅ Memory added.")
        else:
            print(f"⚠️ Memory add failed: {response.text}")
    except Exception as e:
        print(f"Skipping chat memory (endpoint may vary): {e}")

def complex_search(agent_id: str, query: str):
    print("\n" + "="*70)
    print(f"TEST: Complex Search Execution -> '{query}'")
    print("="*70)
    
    url = f"{API_URL}/search_documents"
    payload = {
        "agent_id": agent_id,
        "query": query,
        "top_k": 3
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        print("✅ Search completed.")
        print(f"\nFinal LLM Synthesis:\n{data.get('synthesized_answer')}\n")
        print("Retrieved & Reranked Contexts:")
        for i, res in enumerate(data.get('results', [])):
            text = res.get('text', '').replace('\n', ' ')
            print(f"  [{i+1}] {text[:150]}...")
    else:
        print(f"⚠️ Search failed: {response.text}")

def run_system_test():
    agent_slug = "sys-test-rag-complex-" + uuid.uuid4().hex[:4]
    
    agent_id = create_agent(agent_slug)
    
    if ingest_large_document(agent_id):
        # Allow chroma to flush if needed
        time.sleep(2)
        
        # Add some overlapping conversational context
        add_chat_context(agent_id)
        
        # Execute multiple search scenarios
        print("\n--- SCENARIO 1: Fact Retrieval ---")
        complex_search(agent_id, "What is Shor's algorithm used for and why is it a threat?")
        
        print("\n--- SCENARIO 2: Conceptual Synthesis ---")
        complex_search(agent_id, "Explain quantum decoherence and how many physical qubits are needed to fix it.")
        
        print("\n--- SCENARIO 3: Out of Domain (Should cleanly reject or state unknown) ---")
        complex_search(agent_id, "What is the recipe for making a traditional Italian pizza?")

if __name__ == "__main__":
    run_system_test()
