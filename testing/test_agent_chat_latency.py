import requests
import time
import json

def measure_latency(endpoint_name, url, headers, payload):
    print(f"\nTesting {endpoint_name} endpoint...")
    print(f"URL: {url}")
    
    start_time = time.perf_counter()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        duration = time.perf_counter() - start_time
        
        status_code = response.status_code
        print(f"Status Code: {status_code}")
        
        if status_code == 200:
            resp_json = response.json()
            agent_response = resp_json.get("agent_response", "No agent response found.")
            print(f"Agent Response: {agent_response}")
            return {
                "success": True,
                "latency": duration,
                "status_code": status_code,
                "agent_response": agent_response
            }
        else:
            print(f"Error response: {response.text}")
            return {
                "success": False,
                "latency": duration,
                "status_code": status_code,
                "error": response.text
            }
            
    except Exception as e:
        duration = time.perf_counter() - start_time
        print(f"Exception occurred: {e}")
        return {
            "success": False,
            "latency": duration,
            "status_code": 0,
            "error": str(e)
        }

def run_latency_test():
    print("=" * 70)
    print("Agent Chat Latency Comparison Test")
    print("=" * 70)
    
    # Parameters
    api_key = "sk-JkryNCiUufvPEBvPqaWL9Ptug22JwcUQhGrAl07h8Ts"
    agent_id = "0efda66a-1c17-4fe7-9c9d-b5aa881d9b40"
    message = "Hi there this is Dhruv"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "agent_id": agent_id,
        "message": message
    }
    
    # Endpoints to test
    endpoints = {
        "Local": "http://127.0.0.1:1078/agent_chat",
        "Deployed": "https://www.themanhattanproject.ai/agent_chat"
    }
    
    results = {}
    
    # Run tests
    for name, url in endpoints.items():
        results[name] = measure_latency(name, url, headers, payload)
    
    # Print Comparison Report
    print("\n" + "=" * 70)
    print("LATENCY COMPARISON REPORT")
    print("=" * 70)
    print(f"{'Endpoint':<15} | {'Status':<8} | {'Latency (seconds)':<20} | {'Result Details':<30}")
    print("-" * 80)
    
    for name, result in results.items():
        status_str = "SUCCESS" if result["success"] else "FAILED"
        latency_str = f"{result['latency']:.3f}s"
        
        if result["success"]:
            details = f"Response: {result['agent_response'][:35]}..."
        else:
            details = f"Error Code {result['status_code']}: {str(result.get('error', 'Unknown error'))[:35]}..."
            
        print(f"{name:<15} | {status_str:<8} | {latency_str:<20} | {details:<30}")
    
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_latency_test()
