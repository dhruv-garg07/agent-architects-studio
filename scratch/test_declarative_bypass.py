import requests

url = "http://127.0.0.1:1078/agent_chat"
payload = {
    "agent_id": "60bba348-cafa-4f81-a1ec-5ec65f581957",
    "message": "Because the global economy has become increasingly interconnected in recent decades, multinational corporations must continually adapt their operational strategies to navigate unpredictable market fluctuations while simultaneously addressing the growing environmental and ethical demands of a more socially conscious consumer base."
}
headers = {
    "Authorization": "Bearer sk-JkryNCiUufvPEBvPqaWL9Ptug22JwcUQhGrAl07h8Ts",
    "Content-Type": "application/json"
}

print("Testing declarative seeding query...")
r = requests.post(url, json=payload, headers=headers, timeout=60)
print(f"Status Code: {r.status_code}")
print(f"Response: {r.json().get('agent_response')}")
