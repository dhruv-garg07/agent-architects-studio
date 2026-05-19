import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:5000"
API_KEY = os.getenv("MANHATTAN_API_KEY_TEST", "sk-5VagoCihzX6rWtT0u2L-ZLIfNWDqLV3HhAhdDZ0avW4")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def run_verification():
    print("=== Starting Claude LLM Pipeline Verification ===")
    print(f"Server URL: {BASE_URL}")
    
    # 1. Create Test Agent
    print("\n1. Creating Test Agent...")
    agent_payload = {
        "agent_name": "ClaudeVerifier",
        "agent_slug": "claude-verifier-" + str(int(time.time())),
        "api_key": API_KEY
    }
    r = requests.post(f"{BASE_URL}/create_agent", headers=HEADERS, json=agent_payload)
    if r.status_code not in (200, 201):
        print(f"❌ Failed to create agent (status {r.status_code}): {r.text}")
        return
        
    agent_data = r.json()
    agent_id = agent_data.get("agent_id")
    print(f"✓ Agent Created: {agent_id}")

    try:
        # 2. Add memory entries
        print("\n2. Seeding memories...")
        memory_payload = {
            "agent_id": agent_id,
            "api_key": API_KEY,
            "memories": [
                {
                    "lossless_restatement": "The user's favorite color is electric indigo.",
                    "keywords": ["favorite", "color", "indigo"],
                    "topic": "preferences"
                }
            ]
        }
        r = requests.post(f"{BASE_URL}/add_memory", headers=HEADERS, json=memory_payload)
        print(f"✓ Add Memory Status: {r.status_code}")
        
        print("Waiting for DB indexing...")
        time.sleep(3)

        # 3. Chat and retrieve memory
        print("\n3. Testing recall and Claude generation...")
        chat_payload = {
            "agent_id": agent_id,
            "api_key": API_KEY,
            "message": "What is my favorite color? Answer precisely in a single short sentence."
        }
        
        start_time = time.perf_counter()
        r = requests.post(f"{BASE_URL}/agent_chat", headers=HEADERS, json=chat_payload, timeout=60)
        duration = time.perf_counter() - start_time
        
        print(f"✓ Chat Status Code: {r.status_code}")
        print(f"✓ Latency: {duration:.3f}s")
        
        if r.status_code == 200:
            resp = r.json().get('agent_response')
            print(f"✓ Claude Agent Response:\n   --> {resp}")
            if "electric indigo" in resp.lower():
                print("\n🎉 SUCCESS: Memory successfully retrieved and correctly outputted by Claude!")
            else:
                print("\n⚠️ WARNING: Response returned but expected memory recall was missing.")
        else:
            print(f"❌ Error Response: {r.text}")
            
    finally:
        # 4. Cleanup
        print("\n4. Cleaning up test agent...")
        cleanup_r = requests.post(f"{BASE_URL}/delete_agent", headers=HEADERS, json={"agent_id": agent_id, "api_key": API_KEY})
        print(f"✓ Cleanup Status: {cleanup_r.status_code}")
        print("=== Verification Ended ===")

if __name__ == "__main__":
    run_verification()
