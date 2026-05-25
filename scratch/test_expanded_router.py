import requests
import time

headers = {
    "Authorization": "Bearer sk-JkryNCiUufvPEBvPqaWL9Ptug22JwcUQhGrAl07h8Ts",
    "Content-Type": "application/json"
}

agent_id = "0efda66a-1c17-4fe7-9c9d-b5aa881d9b40"
chat_url = "http://127.0.0.1:1078/agent_chat"

# 1. Test conversational starter
payload_1 = {
    "agent_id": agent_id,
    "message": "Yo! What's up?",
    "strategy": "auto"
}
print("\n--- Test 1: Conversational Starter ---")
start = time.perf_counter()
r1 = requests.post(chat_url, json=payload_1, headers=headers, timeout=60)
print(f"Prompt: '{payload_1['message']}'")
print(f"Latency: {time.perf_counter() - start:.3f}s")
print(f"Response: {r1.json().get('agent_response')}")

# 2. Test short auxiliary
payload_2 = {
    "agent_id": agent_id,
    "message": "Don't you know me?",
    "strategy": "auto"
}
print("\n--- Test 2: Short Auxiliary ---")
start = time.perf_counter()
r2 = requests.post(chat_url, json=payload_2, headers=headers, timeout=60)
print(f"Prompt: '{payload_2['message']}'")
print(f"Latency: {time.perf_counter() - start:.3f}s")
print(f"Response: {r2.json().get('agent_response')}")

# 3. Test declarative info-seeding statement
payload_3 = {
    "agent_id": agent_id,
    "message": "We are working on a timeline of our project: phase 1 is coding, phase 2 is testing.",
    "strategy": "auto"
}
print("\n--- Test 3: Declarative Seeding Statement ---")
start = time.perf_counter()
r3 = requests.post(chat_url, json=payload_3, headers=headers, timeout=60)
print(f"Prompt: '{payload_3['message']}'")
print(f"Latency: {time.perf_counter() - start:.3f}s")
print(f"Response: {r3.json().get('agent_response')}")

# Sleep to allow background indexing
print("\nSleeping for 3 seconds for background thread indexing...")
time.sleep(3)

# 4. Test complex synthesis query
payload_4 = {
    "agent_id": agent_id,
    "message": "Can you summarize the schedule of the project timeline that we are working on?",
    "strategy": "auto"
}
print("\n--- Test 4: Complex Synthesis Query ---")
start = time.perf_counter()
r4 = requests.post(chat_url, json=payload_4, headers=headers, timeout=60)
print(f"Prompt: '{payload_4['message']}'")
print(f"Latency: {time.perf_counter() - start:.3f}s")
print(f"Response: {r4.json().get('agent_response')}")

# 5. Test long multi-clause question
payload_5 = {
    "agent_id": agent_id,
    "message": "If we complete phase 1 by tomorrow, and because Harshit is working on the frontend while Sanket is working on the backend, how does this affect our timeline?",
    "strategy": "auto"
}
print("\n--- Test 5: Long Multi-Clause Question ---")
start = time.perf_counter()
r5 = requests.post(chat_url, json=payload_5, headers=headers, timeout=60)
print(f"Prompt: '{payload_5['message']}'")
print(f"Latency: {time.perf_counter() - start:.3f}s")
print(f"Response: {r5.json().get('agent_response')}")
