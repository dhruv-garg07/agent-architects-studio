import requests
import threading
import time
import sys

BASE_URL = "http://localhost:1078"

def simulate_user():
    print("[USER] Sending prompt: 'Tell me a joke'")
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/call_third_party_llm_service",
            json={"prompt": "Tell me a joke"},
            timeout=70
        )
        duration = time.time() - start_time
        if response.status_code == 200:
            print(f"[USER] Received response in {duration:.2f}s: {response.json()}")
        else:
            print(f"[USER] Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[USER] Request failed: {e}")

def simulate_llm_client():
    print("[CLIENT] Polling for requests...")
    time.sleep(2) # Wait a bit for user request to arrive
    try:
        poll_resp = requests.get(f"{BASE_URL}/llm-poll")
        if poll_resp.status_code == 200:
            data = poll_resp.json()
            if data.get('status') == 'no_requests':
                print("[CLIENT] No requests found.")
                return
            
            request_id = data['request_id']
            prompt = data['prompt']
            print(f"[CLIENT] Got request {request_id}: '{prompt}'")
            
            # Simulate processing time
            time.sleep(1)
            
            print(f"[CLIENT] Sending response for {request_id}")
            resp = requests.post(
                f"{BASE_URL}/llm-respond",
                json={
                    "request_id": request_id,
                    "response": f"This is the LLM response to: {prompt}"
                }
            )
            print(f"[CLIENT] Response status: {resp.status_code}")
        else:
            print(f"[CLIENT] Poll error {poll_resp.status_code}")
    except Exception as e:
        print(f"[CLIENT] Client error: {e}")

if __name__ == "__main__":
    # Start user thread
    user_thread = threading.Thread(target=simulate_user)
    user_thread.start()
    
    # Start client thread
    client_thread = threading.Thread(target=simulate_llm_client)
    client_thread.start()
    
    user_thread.join()
    client_thread.join()
    print("Verification complete.")
