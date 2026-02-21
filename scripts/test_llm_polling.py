import requests
import threading
import time
import sys

BASE_URL = "https://www.console.themanhattanproject.ai"

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
    print("[CLIENT] Initial poll...")
    time.sleep(2) # Wait a bit for user request to arrive
    current_request_id = None
    
    try:
        # Step 1: Initial Poll (GET)
        poll_resp = requests.get(f"{BASE_URL}/llm_poll")
        if poll_resp.status_code == 200:
            data = poll_resp.json()
            if data.get('status') == 'no_requests':
                print("[CLIENT] No requests found on initial poll.")
                return
            
            current_request_id = data['request_id']
            prompt = data['prompt']
            print(f"[CLIENT] Got request {current_request_id}: '{prompt}'")
            
            # Simulate processing time
            time.sleep(1)
            
            # Step 2: Merged response and next job poll (POST)
            print(f"[CLIENT] Sending response for {current_request_id} and polling for next...")
            resp = requests.post(
                f"{BASE_URL}/llm_poll",
                json={
                    "request_id": current_request_id,
                    "response": f"This is the merged response to: {prompt}"
                }
            )
            print(f"[CLIENT] Response/Next poll status: {resp.status_code}")
            if resp.status_code == 200:
                next_job = resp.json()
                if next_job.get('status') == 'no_requests':
                    print("[CLIENT] No more requests available.")
                else:
                    print(f"[CLIENT] Received next job: {next_job.get('request_id')}")
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
