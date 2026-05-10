import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.themanhattanproject.ai"
# API_KEY = os.getenv("MANHATTAN_API_KEY_TEST")
API_KEY = "sk-5VagoCihzX6rWtT0u2L-ZLIfNWDqLV3HhAhdDZ0avW4"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_memory():
    print("--- Starting Agent Memory Test ---")
    
    # 1. Create Agent
    print("\n1. Creating Agent...")
    agent_payload = {
        "agent_name": "MemoryTestAgent2",
        "agent_slug": "memory-test-agent2"
    }
    r = requests.post(f"{BASE_URL}/create_agent", headers=HEADERS, json=agent_payload)
    if r.status_code != 201:
        print(f"Failed to create agent: {r.text}")
        # Try to find existing agent if creation fails (maybe slug exists)
        return
    
    agent_data = r.json()
    agent_id = agent_data.get("agent_id")
    print(f"Agent Created: {agent_id}")

    try:
        # 2. Tell the agent a secret
        print("\n2. Telling agent a secret...")
        chat_payload_1 = {
            "agent_id": agent_id,
            "message": "Hi there! I want you to remember something important: My secret password is 'Antigravity-99'."
        }
        r = requests.post(f"{BASE_URL}/agent_chat", headers=HEADERS, json=chat_payload_1)
        print(f"Chat 1 Status: {r.status_code}")
        print(f"Agent Response: {r.json().get('agent_response')}")

        # Wait a bit for indexing if necessary (SimpleMem usually handles this in finalize)
        print("\nWaiting for memory indexing...")
        time.sleep(5)

        # 3. Ask the agent about the secret
        print("\n3. Testing recall...")
        chat_payload_2 = {
            "agent_id": agent_id,
            "message": "Hey, do you remember what my secret password was?"
        }
        r = requests.post(f"{BASE_URL}/agent_chat", headers=HEADERS, json=chat_payload_2)
        print(f"Chat 2 Status: {r.status_code}")
        response_text = r.json().get('agent_response')
        print(f"Agent Response: {response_text}")

        if "Antigravity-99" in response_text:
            print("\n✅ SUCCESS: Agent remembered the secret!")
        else:
            print("\n❌ FAILURE: Agent did not recall the secret.")

    finally:
        # 4. Cleanup
        print("\n4. Cleaning up agent...")
        requests.post(f"{BASE_URL}/delete_agent", headers=HEADERS, json={"agent_id": agent_id})
        print("Agent deleted.")

if __name__ == "__main__":
    test_memory()
