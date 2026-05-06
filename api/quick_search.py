import httpx

import os
from dotenv import load_dotenv
load_dotenv()

r = httpx.post(
    'https://www.themanhattanproject.ai/read_memory', 
    json={'agent_id': 'mcp-test-agent', 'query': 'What does the user like?', 'top_k': 5}, 
    headers={
        'Content-Type': 'application/json', 
        'Authorization': f'Bearer {os.getenv("MANHATTAN_API_KEY_TEST")}'
    }, 
    timeout=60
)

print('Search Results:')
data = r.json()
for x in data.get('results', []):
    print(f"  - {x.get('lossless_restatement', '')}")
