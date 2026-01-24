"""
Demo script using the SDK (Requires running server).
Run `python -m gitmem.api.server` first (or the flask app).
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from gitmem.sdk.client import GitMemClient

def run_sdk_demo():
    client = GitMemClient(base_url="http://localhost:5000/gitmem/api")
    
    try:
        print("Adding memory...")
        mid = client.add_memory("agent_x", "I am a helpful assistant.", "semantic")
        print(f"Memory added: {mid}")
        
        print("Querying...")
        results = client.query("agent_x", "helpful")
        print("Results:", results)
    except Exception as e:
        print("Server not running or error:", e)

if __name__ == "__main__":
    run_sdk_demo()
