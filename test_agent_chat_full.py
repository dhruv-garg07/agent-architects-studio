import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

# BASE_URL = "http://localhost:1080"
BASE_URL = "https://www.themanhattanproject.ai"
API_KEY = os.getenv("MANHATTAN_API_KEY_TEST", "sk-5VagoCihzX6rWtT0u2L-ZLIfNWDqLV3HhAhdDZ0avW4")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_full_workflow():
    print("--- Starting Full Agent Chat & Memory Test ---")
    
    # 1. Create Agent
    print("\n1. Creating Agent...")
    agent_payload = {
        "agent_name": "RecallMaster",
        "agent_slug": "recall-master-" + str(int(time.time())),
        "api_key": API_KEY
    }
    r = requests.post(f"{BASE_URL}/create_agent", headers=HEADERS, json=agent_payload)
    if r.status_code != 201:
        print(f"Failed to create agent: {r.text}")
        return
    
    agent_data = r.json()
    agent_id = agent_data.get("agent_id")
    print(f"Agent Created: {agent_id}")

    try:
        # 2. Push direct data (The "Memory" part)
        print("\n2. Pushing direct data into memory (without LLM)...")
        memory_payload = {
            "agent_id": agent_id,
            "api_key": API_KEY,
            "memories": [
                {
                    "lossless_restatement": "The secret code for the vault is 'XEBRA-2026'.",
                    "keywords": ["secret", "vault", "code"],
                    "topic": "security"
                },
                {
                    "lossless_restatement": "The office is located on the 42nd floor of the Manhattan Tower.",
                    "keywords": ["office", "location", "floor"],
                    "topic": "info"
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/add_memory", headers=HEADERS, json=memory_payload)
        print(f"Add Memory Status: {r.status_code}")
        print(f"Response: {r.json()}")

        # Wait for indexing
        print("\nWaiting for indexing...")
        time.sleep(5)

        # 3. Chat and test recall
        print("\n3. Testing recall via /agent_chat...")
        test_questions = [
            "What is the secret code for the vault?",
            "Where is the office located?"
        ]

        for question in test_questions:
            print(f"\nQuestion: {question}")
            chat_payload = {
                "agent_id": agent_id,
                "api_key": API_KEY,
                "message": question
            }
            try:
                r = requests.post(f"{BASE_URL}/agent_chat", headers=HEADERS, json=chat_payload, timeout=60)
                print(f"Chat Status: {r.status_code}")
                if r.status_code == 200:
                    resp = r.json().get('agent_response')
                    print(f"Agent Response: {resp}")
                else:
                    print(f"Error Response: {r.text}")
            except Exception as e:
                print(f"Request failed: {e}")

    finally:
        # 4. Cleanup
        print("\n4. Cleaning up agent...")
        requests.post(f"{BASE_URL}/delete_agent", headers=HEADERS, json={"agent_id": agent_id, "api_key": API_KEY})
        print("Agent deleted.")

if __name__ == "__main__":
    test_full_workflow()
