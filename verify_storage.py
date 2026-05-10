import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:1079"
# API_KEY = os.getenv("MANHATTAN_API_KEY_TEST")
API_KEY = "sk-5VagoCihzX6rWtT0u2L-ZLIfNWDqLV3HhAhdDZ0avW4"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def verify_storage():
    print("--- Verifying Agent Memory Storage (Direct DB Check) ---")
    
    # 1. Create Agent
    print("\n1. Creating Agent...")
    agent_id = "storage-test-" + str(int(time.time()))
    agent_payload = {
        "agent_name": "StorageTester",
        "agent_slug": agent_id
    }
    r = requests.post(f"{BASE_URL}/create_agent", headers=HEADERS, json=agent_payload)
    if r.status_code != 201:
        print(f"Failed to create agent: {r.text}")
        return
    
    agent_id = r.json().get("agent_id")
    print(f"Agent Created: {agent_id}")

    try:
        # 2. Push direct data
        print("\n2. Pushing test memory...")
        secret_content = "The verification code is ALPHA-OMEGA-99."
        memory_payload = {
            "agent_id": agent_id,
            "memories": [
                {
                    "lossless_restatement": secret_content,
                    "memory_type": "episodic",
                    "topic": "verification"
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/add_memory", headers=HEADERS, json=memory_payload)
        print(f"Add Memory Status: {r.status_code}")

        # 3. Verify via get_memories_by_bin (Bypasses LLM)
        print("\n3. Verifying storage via /get_memories_by_bin...")
        bin_payload = {
            "agent_id": agent_id,
            "memory_type": "episodic",
            "limit": 10
        }
        r = requests.post(f"{BASE_URL}/get_memories_by_bin", headers=HEADERS, json=bin_payload)
        print(f"Get Memories Status: {r.status_code}")
        
        if r.status_code == 200:
            results = r.json().get('memories', [])
            found = False
            for mem in results:
                print(f"Found Memory: {mem.get('lossless_restatement')}")
                if secret_content in mem.get('lossless_restatement'):
                    found = True
            
            if found:
                print("\n✅ SUCCESS: Data was pushed and retrieved from database!")
            else:
                print("\n❌ FAILURE: Data not found in database.")
        else:
            print(f"Error: {r.text}")

    finally:
        # 4. Cleanup
        print("\n4. Cleaning up...")
        requests.post(f"{BASE_URL}/delete_agent", headers=HEADERS, json={"agent_id": agent_id})
        print("Done.")

if __name__ == "__main__":
    verify_storage()
