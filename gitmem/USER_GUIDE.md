# 📘 GITMEM User Guide

**GITMEM** is the world's first version-controlled memory system for Autonomous AI Agents. Just as developers use Git to manage code, GITMEM allows you to manage, branch, diff, and revert the actual *cognition* and *knowledge* of your AI agents.

---

## 🚀 Quick Start

### 1. Requirements
Ensure the GITMEM server is running:
```bash
python api/index.py
```
*Port `1078` is used by default.*

### 2. Initialize the Client
In your Python application or agent script:

```python
from gitmem.sdk import GitMem, EpisodicMemory, MemoryScope

# Connect to the local GITMEM server
client = GitMem(base_url="http://localhost:1078")
```

---

## 🧠 Core Workflows

### 1. Adding Memory
Agents constantly generate new thoughts, observations, and facts.

```python
# Add a simple memory
client.add({
    "content": "User prefers concise Python code.",
    "agent_id": "agent-alpha-1",
    "type": "episodic"
})

# Add a structured memory (Recommended)
memory = EpisodicMemory(
    agent_id="agent-alpha-1",
    content="The project deadline is Q3 2026.",
    scope=MemoryScope.SHARED,
    importance=0.9
)
# 'auto_commit' immediately saves a snapshot
client.add(memory, auto_commit=True)
```

### 2. Retrieval (Semantic Search)
Retrieve relevant context for your agent based on the current task.

```python
# Search for relevant memories
results = client.query(
    query="What does the user like?", 
    agent_id="agent-alpha-1"
)

# Get an LLM-ready context string
context_str = client.get_context(
    agent_id="agent-alpha-1", 
    query="Code style preferences",
    token_limit=1000
)

# Inject into your LLM prompt
prompt = f"""
System: You are a helpful assistant.
Context:
{context_str}

User: Write a Fibonacci function.
"""
```

### 3. Version Control (The "Git" in GitMem)

#### Commit (Snapshot)
Save the state of an agent's mind. Useful after a successful task completion or major learning event.

```python
commit = client.commit(
    agent_id="agent-alpha-1", 
    message="Completed initialization task, learned user preferences"
)
print(f"Saved state: {commit.hash}")
```

#### Diff (Compare)
See how an agent's memory has changed between two points in time.

```python
# Compare current state (HEAD) with a previous commit
diff = client.diff(
    agent_id="agent-alpha-1",
    commit_a="a1b2c3d4", # Old
    commit_b="e5f6g7h8"  # New
)
print(f"New Memories: {diff.added}")
```

#### Rollback (Undo)
If an agent hallucinates or learns incorrect information, you can revert its brain to a known good state.

```python
# Restore memory to a previous safe state
client.rollback(
    agent_id="agent-alpha-1",
    commit_hash="a1b2c3d4"
)
```

#### Fork (Branch/Clone)
Create a copy of an agent to experiment with a new task without polluting the original's memory.

```python
# Clone 'agent-alpha-1' to create 'agent-alpha-experimental'
new_head = client.fork(
    source_agent_id="agent-alpha-1", 
    new_branch_name="agent-alpha-experimental"
)
```

---

## 🏗️ Architecture Concepts

| Concept | Description |
| :--- | :--- |
| **Memory Item** | An individual unit of information (Thought, Fact, Event). Immutable once created. |
| **Commit** | A snapshot of the entire set of accessible memories for an agent at a specific time. |
| **HEAD** | The pointer to the current active commit for an agent. |
| **Fork** | Creating a new lineage of memory starting from a specific commit. |
| **Scope** | `Private` (Agent only), `Shared` (Team/Swarm), `Global` (Universal). |

---

## 🔌 API Reference

**Base URL**: `http://localhost:1078/gitmem/api`

### Endpoints

*   `POST /memory`: Add a memory item.
*   `POST /query`: Semantic search.
*   `POST /commit`: Create a snapshot.
    *   **Body**: `{"agent_id": "...", "message": "..."}`
*   `POST /diff`: Compare commits.
    *   **Body**: `{"commit_a": "...", "commit_b": "..."}`
*   `POST /rollback`: Revert state.
    *   **Body**: `{"agent_id": "...", "hash": "..."}`
*   `POST /fork`: Clone agent memory.
    *   **Body**: `{"source": "...", "target": "..."}`

---

## 🛠️ Best Practices

1.  **Commit Frequently**: Just like code, commit often (e.g., after every user session or major task).
2.  **Use Types**: Distinguish between `episodic` (what happened) and `semantic` (what is true).
3.  **Fork for Experiments**: Never let an agent learn experimental data in its main branch. Fork it, run the simulation, then discard or merge (manual merge for now).
4.  **Tag Metadata**: Use the `metadata` dictionary to store `source`, `confidence`, or `tags` for better filtering later.
