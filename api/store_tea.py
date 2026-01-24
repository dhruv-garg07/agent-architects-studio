import asyncio
import httpx
import json
import os

# Configuration from mcp_memory_client.py
API_URL = "https://www.themanhattanproject.ai"
API_KEY = "sk-cc5yYQQXdiN66pADVmlT8vcg_296O0vbX5VcqTec3Ts"
TARGET_AGENT_ID = "84aab1f8-3ea9-4c6a-aa3c-cd8eaa274a5e"

async def call_api(endpoint, payload):
    url = f"{API_URL}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

async def main():
    memory = {
        "lossless_restatement": "The user loves tea.",
        "keywords": ["tea", "love", "preference"],
        "topic": "user preferences"
    }
    print(f"Storing memory: {memory}")
    result = await call_api("add_memory", {
        "agent_id": TARGET_AGENT_ID,
        "memories": [memory]
    })
    print(f"Result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
