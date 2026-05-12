import requests
import json

BASE_URL = "http://localhost:1078"
API_KEY = "sk-4V8___QOM3ktVACbniXwdpxK7TXK_Zx39GnGWNFiyvI"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def print_section(title):
    print(f"\n{'='*10} {title} {'='*10}")

def test_create_agent():
    print_section("Testing /create_agent")
    payload = {
        "agent_name": "Testing CRUD Agent",
        "agent_slug": "testing-crud-agent",
        "permissions": {"memory": True, "llm": True},
        "limits": {"requests_per_min": 60},
        "system_prompt": "You are a test agent.",
        "metadata": {"environment": "testing"}
    }
    url = f"{BASE_URL}/create_agent"
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            data = response.json()
            print(f"Response JSON:\n{json.dumps(data, indent=2)}")
            # Extract agent_id (could be under 'agent_id' or 'id')
            agent_id = data.get("agent_id") or data.get("id")
            return agent_id
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
            return None
    except Exception as e:
        print(f"Error connecting to {url}: {e}")
        return None

def test_list_agents():
    print_section("Testing /list_agents")
    url = f"{BASE_URL}/list_agents"
    print(f"GET {url}")
    try:
        response = requests.get(url, headers=HEADERS)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_get_agent(agent_id):
    print_section(f"Testing /get_agent for {agent_id}")
    url = f"{BASE_URL}/get_agent"
    print(f"GET {url}")
    payload = {"agent_id": agent_id}
    try:
        response = requests.get(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_update_agent(agent_id):
    print_section(f"Testing /update_agent for {agent_id}")
    url = f"{BASE_URL}/update_agent"
    print(f"POST {url}")
    payload = {
        "agent_id": agent_id,
        "updates": {
            "agent_name": "Updated Testing CRUD Agent",
            "system_prompt": "You are an updated test agent."
        }
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_disable_agent(agent_id):
    print_section(f"Testing /disable_agent for {agent_id}")
    url = f"{BASE_URL}/disable_agent"
    print(f"POST {url}")
    payload = {"agent_id": agent_id}
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_enable_agent(agent_id):
    print_section(f"Testing /enable_agent for {agent_id}")
    url = f"{BASE_URL}/enable_agent"
    print(f"POST {url}")
    payload = {"agent_id": agent_id}
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_delete_agent(agent_id):
    print_section(f"Testing /delete_agent for {agent_id}")
    url = f"{BASE_URL}/delete_agent"
    print(f"POST {url}")
    payload = {"agent_id": agent_id}
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON:\n{json.dumps(response.json(), indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Text:\n{response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print(f"Starting Agent CRUD API Tests targeting {BASE_URL}")
    agent_id = test_create_agent()
    if agent_id:
        print(f"\nSuccessfully created agent with ID: {agent_id}")
        test_list_agents()
        test_get_agent(agent_id)
        test_update_agent(agent_id)
        test_disable_agent(agent_id)
        test_enable_agent(agent_id)
        test_delete_agent(agent_id)
    else:
        print("\nFailed to create agent. Check if the API server is running on port 1078.")
