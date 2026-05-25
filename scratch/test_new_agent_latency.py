import requests
import time

headers = {
    "Authorization": "Bearer sk-JkryNCiUufvPEBvPqaWL9Ptug22JwcUQhGrAl07h8Ts",
    "Content-Type": "application/json"
}

agent_id = "0efda66a-1c17-4fe7-9c9d-b5aa881d9b40"

# 1. Clear the database collection for the valid agent to ensure it is completely empty
clear_url = "http://127.0.0.1:1078/create_memory"
clear_payload = {
    "agent_id": agent_id,
    "clear_db": True
}

print(f"1. Clearing ChromaDB collection for agent {agent_id} to ensure empty state...")
clear_resp = requests.post(clear_url, json=clear_payload, headers=headers, timeout=60)
if clear_resp.status_code not in (200, 201):
    print(f"Failed to clear database: {clear_resp.text}")
    exit(1)
print("Collection cleared successfully!")

# 2. Test auto-routing on a DECLARATIVE introduction
chat_url = "http://127.0.0.1:1078/agent_chat"
payload_1 = {
    "agent_id": agent_id,
    "message": "Hi, I am working on a startup named Manhatan Project. I am Dhruv and I have my fellow co-founders Harshit and Sanket",
    "strategy": "auto"
}

print(f"\n2. Sending declarative statement with 'strategy: auto' (should auto-route to FAST mode)...")
start_time = time.perf_counter()
resp_1 = requests.post(chat_url, json=payload_1, headers=headers, timeout=60)
latency_1 = time.perf_counter() - start_time
print(f"Status Code: {resp_1.status_code}")
print(f"Response: {resp_1.json().get('agent_response')}")
print(f"Latency: {latency_1:.3f} seconds")

# Sleep for background database indexing
print("\nSleeping for 3 seconds for background thread indexing...")
time.sleep(3)

# 3. Test auto-routing on a SIMPLE question
payload_2 = {
    "agent_id": agent_id,
    "message": "Who are my co-founders?",
    "strategy": "auto"
}

print(f"\n3. Sending simple question with 'strategy: auto' (should auto-route to FAST mode)...")
start_time = time.perf_counter()
resp_2 = requests.post(chat_url, json=payload_2, headers=headers, timeout=60)
latency_2 = time.perf_counter() - start_time
print(f"Status Code: {resp_2.status_code}")
print(f"Response: {resp_2.json().get('agent_response')}")
print(f"Latency: {latency_2:.3f} seconds")

# 4. Test auto-routing on a COMPLEX query
payload_3 = {
    "agent_id": agent_id,
    "message": "What is the difference between my co-founders?",
    "strategy": "auto"
}

print(f"\n4. Sending complex comparison question with 'strategy: auto' (should auto-route to THINKING mode)...")
start_time = time.perf_counter()
resp_3 = requests.post(chat_url, json=payload_3, headers=headers, timeout=60)
latency_3 = time.perf_counter() - start_time
print(f"Status Code: {resp_3.status_code}")
print(f"Response: {resp_3.json().get('agent_response')}")
print(f"Latency: {latency_3:.3f} seconds")
