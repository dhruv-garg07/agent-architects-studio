# API Examples Plan

> **Status:** Pending URL decision  
> **Note:** The base URL / hosting location for these examples is TBD — update `BASE_URL` placeholders once decided.

---

## Overview

Each API category below has a set of planned examples. Each example is a self-contained, runnable script (Python, JavaScript, cURL) that demonstrates a realistic end-to-end workflow — not just a single API call.

---

## Category 1 — Agents

### Example 1.1: Full Agent Lifecycle
**Goal:** Create → configure → disable → re-enable → delete an agent.  
**Languages:** Python, JavaScript, cURL  
**Steps:**
1. `POST /create_agent` — create with a unique slug
2. `GET /list_agents` — verify it appears
3. `POST /update_agent` — change the description
4. `POST /disable_agent` — disable it
5. `POST /enable_agent` — re-enable it
6. `POST /delete_agent` — permanent cleanup

**File targets (when URL decided):**
- `examples/agents/lifecycle.py`
- `examples/agents/lifecycle.js`
- `examples/agents/lifecycle.sh`

---

### Example 1.2: Multi-Turn Chat Session
**Goal:** Create an agent, have a multi-turn conversation, track conversation_id.  
**Languages:** Python, JavaScript  
**Steps:**
1. `POST /create_agent`
2. `POST /agent_chat` — turn 1 (no conversation_id)
3. `POST /agent_chat` — turn 2 (pass conversation_id from turn 1)
4. `POST /agent_chat` — turn 3 (continue the thread)

**File targets:**
- `examples/agents/multi_turn_chat.py`
- `examples/agents/multi_turn_chat.js`

---

## Category 2 — Documents

### Example 2.1: Bulk Document Upload & Search
**Goal:** Upload a set of documents then run semantic search queries.  
**Languages:** Python, cURL  
**Steps:**
1. `POST /create_agent` (or use existing)
2. `POST /add_document` — upload 3+ documents in one call
3. `POST /search_documents` — semantic query, inspect results
4. `POST /update_document` — update one document
5. `POST /search_documents` — re-run same query to see updated results

**File targets:**
- `examples/documents/bulk_upload_and_search.py`
- `examples/documents/bulk_upload_and_search.sh`

---

### Example 2.2: Knowledge Base Q&A Bot
**Goal:** Build a minimal RAG Q&A bot using documents + agent_chat.  
**Languages:** Python  
**Steps:**
1. Create agent
2. Upload FAQ documents with `POST /add_document`
3. Loop: accept user question → call `POST /agent_chat` → print answer

**File targets:**
- `examples/documents/rag_qa_bot.py`

---

## Category 3 — Memory

### Example 3.1: Memory Initialization & Direct Storage
**Goal:** Initialize memory, store facts directly, then retrieve them.  
**Languages:** Python, JavaScript  
**Steps:**
1. `POST /create_agent`
2. `POST /create_memory` — init the memory system
3. `POST /add_memory` — store 3 structured facts
4. `POST /read_memory` — query and inspect retrieval scores
5. `POST /get_context` — ask a question, get LLM answer + sources

**File targets:**
- `examples/memory/init_and_store.py`
- `examples/memory/init_and_store.js`

---

### Example 3.2: Dialogue-to-Memory Pipeline
**Goal:** Process a real conversation transcript through process_raw, then query it.  
**Languages:** Python  
**Steps:**
1. Create agent + init memory
2. `POST /process_raw` — feed a multi-turn dialogue transcript
3. `POST /read_memory` — verify extracted memories
4. `POST /get_context` — ask a question grounded in the dialogue

**File targets:**
- `examples/memory/dialogue_pipeline.py`

---

### Example 3.3: Persistent Memory Across Sessions
**Goal:** Show that memories survive across two separate script invocations.  
**Languages:** Python  
**Steps:**
- Session A: create agent, init memory, store facts, print agent_id
- Session B (separate run): load same agent_id, call `POST /get_context` to prove recall

**File targets:**
- `examples/memory/session_a_store.py`
- `examples/memory/session_b_recall.py`

---

## Category 4 — Analytics & Stats

### Example 4.1: Dashboard Data Pull
**Goal:** Fetch agent stats, API usage, and health in one script.  
**Languages:** Python, cURL  
**Steps:**
1. `GET /agent_stats` — per-agent usage counts
2. `GET /api_usage` — account-level call volumes
3. `GET /health_detailed` — system health check

**File targets:**
- `examples/analytics/dashboard_pull.py`
- `examples/analytics/dashboard_pull.sh`

---

## Category 5 — Data Portability

### Example 5.1: Export → Import Round-Trip
**Goal:** Export an agent's data, then re-import it to a new agent.  
**Languages:** Python  
**Steps:**
1. `POST /export` — export all data for agent A
2. Save export to local JSON file
3. `POST /create_agent` — create agent B
4. `POST /import` — import the saved export into agent B
5. `POST /import_summary` — verify counts match

**File targets:**
- `examples/portability/export_import_roundtrip.py`

---

## Example Page Structure (when URL is decided)

Each example page on the documentation site should contain:

| Section | Content |
|---------|---------|
| **Title** | Descriptive name (e.g. "Multi-Turn Chat Session") |
| **Difficulty** | Beginner / Intermediate / Advanced |
| **Prerequisites** | Endpoints needed, env vars to set |
| **Overview** | 2–3 sentence description of what the example does and why |
| **Setup** | `pip install requests` or `npm install` etc. |
| **Full Code** | Syntax-highlighted, copy-able, with inline comments |
| **Expected Output** | Sample console output so users can verify it works |
| **Next Steps** | Link to the next logical example in the sequence |

---

## Suggested URL Structure

Once the hosting location is decided, replace `BASE_EXAMPLES_URL` below:

```
BASE_EXAMPLES_URL = "<!-- TBD -->"

Examples would live at:
  {BASE_EXAMPLES_URL}/agents/lifecycle
  {BASE_EXAMPLES_URL}/agents/multi-turn-chat
  {BASE_EXAMPLES_URL}/documents/bulk-upload
  {BASE_EXAMPLES_URL}/documents/rag-qa-bot
  {BASE_EXAMPLES_URL}/memory/init-and-store
  {BASE_EXAMPLES_URL}/memory/dialogue-pipeline
  {BASE_EXAMPLES_URL}/memory/persistent-sessions
  {BASE_EXAMPLES_URL}/analytics/dashboard
  {BASE_EXAMPLES_URL}/portability/export-import
```

---

## Notes

- All examples should read `BASE_URL` and `API_KEY` from environment variables (`os.environ` / `process.env`), never hardcoded.
- Python examples require only `requests` (standard install).
- JavaScript examples should work in both Node.js 18+ and modern browsers (using native `fetch`).
- Each example should be runnable end-to-end from a fresh state with no prior setup other than having a valid API key.
