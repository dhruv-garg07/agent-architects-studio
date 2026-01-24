# GITMEM

A GitHub-like system for AI agent memory.

## Structure
- `/agents`: Agent profiles and states.
- `/memory`: Global memory stores.
- `/indexes`: Vector database persistence.
- `gitmem/sdk`: Python Client SDK.

## Getting Started

### Installation
Ensure you have the required dependencies:
```bash
pip install requests pydantic
```

### Usage (Python SDK)

You can interact with GITMEM programmatically using the SDK:

```python
from gitmem.sdk import GitMem

# Initialize client
client = GitMem(base_url="http://localhost:5000")

# Add a memory
client.add_memory(
    content="The user prefers dark mode for all UI components.",
    agent_id="agent-007",
    memory_type="preference",
    metadata={"confidence": 0.9}
)

# Search memories
results = client.query("Waht does the user like?", agent_id="agent-007")
print(results)

# Commit state (Snapshot)
client.commit(agent_id="agent-007", message="Saved initial user preferences")
```

## Running the Server
The GITMEM API is integrated into the main application. 
Run the Flask app normally:
```bash
python api/index.py
```
