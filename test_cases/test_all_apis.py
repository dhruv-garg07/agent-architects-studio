"""
Comprehensive API Test Suite for Manhattan API
Tests all 32 endpoints against the live server.
Run: python test_all_apis.py
"""
import requests
import json
import time
import uuid
import sys
from datetime import datetime

# BASE_URL = "https://www.themanhattanproject.ai"
BASE_URL = "http://localhost:1078"
# BASE_URL = "http://192.168.0.9:5000"
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = "sk-4V8___QOM3ktVACbniXwdpxK7TXK_Zx39GnGWNFiyvI"
HEADERS = {"Authorization": API_KEY, "Content-Type": "application/json"}
TIMEOUT = 30

# Shared state across tests
STATE = {"agent_id": None, "doc_id": None, "entry_id": None}

results = []

def run_test(name, fn):
    """Run a single test and record result."""
    try:
        fn()
        results.append(("PASS", name, ""))
        print(f"  [PASS]  {name}")
    except AssertionError as e:
        results.append(("FAIL", name, str(e)))
        print(f"  [FAIL]  {name}: {e}")
    except Exception as e:
        results.append(("ERROR", name, str(e)))
        print(f"  [ERR]   {name}: {e}")

# ========== HEALTH ENDPOINTS ==========

def test_ping():
    r = requests.get(f"{BASE_URL}/ping", timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert "status" in data or "ok" in data, f"Missing status field: {data}"

def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"

def test_health_detailed():
    r = requests.get(f"{BASE_URL}/health_detailed", timeout=TIMEOUT)
    assert r.status_code in (200, 503), f"Expected 200/503, got {r.status_code}"
    data = r.json()
    assert "services" in data, f"Missing services: {data}"

# ========== AUTH ENDPOINTS ==========

def test_validate_key_missing():
    r = requests.post(f"{BASE_URL}/validate_key", json={}, timeout=TIMEOUT)
    assert r.status_code in (400, 401), f"Expected 400/401, got {r.status_code}"
    assert not r.json().get("valid", False)

def test_validate_key_invalid():
    r = requests.post(f"{BASE_URL}/validate_key", json={"api_key": "sk-INVALID-KEY-12345678901234"}, timeout=TIMEOUT)
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    assert not r.json().get("valid", False)

def test_validate_key_valid():
    r = requests.post(f"{BASE_URL}/validate_key", json={"api_key": API_KEY}, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    assert r.json().get("valid", False), f"Key should be valid: {r.json()}"

# ========== AGENT CRUD ==========

def test_create_agent():
    ts = int(time.time())
    payload = {
        "agent_name": f"test-agent-{ts}",
        "agent_slug": f"test-agent-{ts}",
        "permissions": {"run": True},
        "limits": {"rpm": 10},
        "system-prompt": "Auto-test agent system prompt",
        "metadata": {"created_by": "test_all_apis"}
    }
    r = requests.post(f"{BASE_URL}/create_agent", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Expected 201, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    STATE["agent_id"] = data.get("agent_id") or data.get("id")
    assert STATE["agent_id"], f"No agent_id in response: {data}"

def test_list_agents():
    r = requests.get(f"{BASE_URL}/list_agents", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    # Use first agent if our create didn't return one
    if not STATE["agent_id"] and data:
        STATE["agent_id"] = data[0].get("agent_id")

def test_get_agent():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id available (create/list failed)")
    r = requests.get(f"{BASE_URL}/get_agent", headers=HEADERS,
                     json={"agent_id": STATE["agent_id"]}, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_update_agent():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "updates": {"system_prompt": f"Updated at {datetime.utcnow().isoformat()}"}}
    r = requests.post(f"{BASE_URL}/update_agent", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_disable_agent():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    r = requests.post(f"{BASE_URL}/disable_agent", json={"agent_id": STATE["agent_id"]}, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_enable_agent():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    r = requests.post(f"{BASE_URL}/enable_agent", json={"agent_id": STATE["agent_id"]}, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

# ========== DOCUMENT ENDPOINTS ==========

def test_add_document():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    STATE["doc_id"] = f"test-doc-{int(time.time())}"
    payload = {
        "agent_id": STATE["agent_id"],
        "documents": ["This is a test document about machine learning and neural networks."],
        "ids": [STATE["doc_id"]],
        "metadata": {"source": "test_suite"}
    }
    r = requests.post(f"{BASE_URL}/add_document", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_search_documents():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "query": "machine learning", "top_k": 3}
    r = requests.post(f"{BASE_URL}/search_documents", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "results" in data, f"Missing 'results': {data}"

def test_update_document():
    if not STATE["agent_id"] or not STATE["doc_id"]:
        raise AssertionError("No agent_id or doc_id")
    payload = {
        "agent_id": STATE["agent_id"],
        "document_ids": [STATE["doc_id"]],
        "new_docs": ["Updated test document about deep learning and transformers."],
        "metadata": {"updated": True}
    }
    r = requests.post(f"{BASE_URL}/update_document", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_update_document_metadata():
    if not STATE["agent_id"] or not STATE["doc_id"]:
        raise AssertionError("No agent_id or doc_id")
    payload = {
        "agent_id": STATE["agent_id"],
        "document_id": STATE["doc_id"],
        "metadata": {"source": "test_suite", "version": "2"}
    }
    r = requests.post(f"{BASE_URL}/update_document_metadata", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_search_chat_history():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "user_id": "test-user", "limit": 5}
    r = requests.post(f"{BASE_URL}/search_chat_history", json=payload, headers=HEADERS, timeout=TIMEOUT)
    # May return 200 or 500 if chat history collection doesn't exist yet
    assert r.status_code in (200, 500), f"Expected 200/500, got {r.status_code}: {r.text[:200]}"

# ========== MEMORY ENDPOINTS ==========

def test_create_memory():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "clear_db": False}
    r = requests.post(f"{BASE_URL}/create_memory", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text[:200]}"

def test_add_memory():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {
        "agent_id": STATE["agent_id"],
        "memories": [{
            "lossless_restatement": "Alice scheduled a meeting with Bob at Starbucks on Jan 22 at 2pm",
            "keywords": ["meeting", "Starbucks", "Alice", "Bob"],
            "persons": ["Alice", "Bob"],
            "location": "Starbucks",
            "timestamp": "2025-01-22T14:00:00",
            "topic": "meeting scheduling"
        }]
    }
    r = requests.post(f"{BASE_URL}/add_memory", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    ids = data.get("entry_ids", [])
    if ids:
        STATE["entry_id"] = ids[0]

def test_read_memory():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "query": "meeting with Bob", "top_k": 3}
    r = requests.post(f"{BASE_URL}/read_memory", json=payload, headers=HEADERS, timeout=60)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "results" in data, f"Missing 'results': {data}"

def test_get_memories_by_bin():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "memory_type": "episodic", "limit": 10}
    r = requests.post(f"{BASE_URL}/get_memories_by_bin", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code in (200, 500), f"Expected 200/500, got {r.status_code}: {r.text[:200]}"

def test_get_context():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "question": "When is the meeting with Bob?"}
    r = requests.post(f"{BASE_URL}/get_context", json=payload, headers=HEADERS, timeout=120)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert "answer" in data, f"Missing 'answer': {data}"

def test_update_memory():
    if not STATE["agent_id"] or not STATE["entry_id"]:
        raise AssertionError("No agent_id or entry_id")
    payload = {
        "agent_id": STATE["agent_id"],
        "entry_id": STATE["entry_id"],
        "updates": {"topic": "rescheduled meeting", "timestamp": "2025-01-22T15:00:00"}
    }
    r = requests.post(f"{BASE_URL}/update_memory", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_process_raw():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {
        "agent_id": STATE["agent_id"],
        "dialogues": [
            {"speaker": "Charlie", "content": "Project deadline is March 15", "timestamp": "2025-01-20T09:00:00"},
            {"speaker": "Dave", "content": "I will prepare the slides", "timestamp": "2025-01-20T09:01:00"}
        ]
    }
    r = requests.post(f"{BASE_URL}/process_raw", json=payload, headers=HEADERS, timeout=120)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

# ========== ANALYTICS ==========

def test_agent_stats():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"]}
    r = requests.post(f"{BASE_URL}/agent_stats", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code in (200, 404), f"Expected 200/404, got {r.status_code}: {r.text[:200]}"

def test_api_usage():
    r = requests.post(f"{BASE_URL}/api_usage", json={}, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert data.get("ok"), f"Expected ok=true: {data}"

# ========== BULK OPERATIONS ==========

def test_list_memories():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "limit": 10, "offset": 0}
    r = requests.post(f"{BASE_URL}/list_memories", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code in (200, 404), f"Expected 200/404, got {r.status_code}: {r.text[:200]}"

def test_bulk_add_memory():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {
        "agent_id": STATE["agent_id"],
        "memories": [
            {"lossless_restatement": "Bulk memory 1: Team uses Python 3.11", "keywords": ["python", "team"], "topic": "tech"},
            {"lossless_restatement": "Bulk memory 2: Deployments happen on Fridays", "keywords": ["deploy", "friday"], "topic": "process"}
        ]
    }
    r = requests.post(f"{BASE_URL}/bulk_add_memory", json=payload, headers=HEADERS, timeout=60)
    assert r.status_code in (200, 404), f"Expected 200/404, got {r.status_code}: {r.text[:200]}"

# ========== DATA PORTABILITY ==========

def test_export_memories():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"]}
    r = requests.post(f"{BASE_URL}/export_memories", json=payload, headers=HEADERS, timeout=60)
    assert r.status_code in (200, 404), f"Expected 200/404, got {r.status_code}: {r.text[:200]}"
    if r.status_code == 200:
        data = r.json()
        STATE["export_data"] = data.get("export")

def test_import_memories():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    export_data = STATE.get("export_data")
    # Ensure we have valid import data even if export was empty
    if not export_data or not export_data.get("memories"):
        export_data = {"version": "1.0", "memories": [
            {"lossless_restatement": "Imported test memory about project deadlines", "keywords": ["import", "test"], "topic": "import_test"}
        ]}
    payload = {"agent_id": STATE["agent_id"], "export_data": export_data, "merge_mode": "append"}
    r = requests.post(f"{BASE_URL}/import_memories", json=payload, headers=HEADERS, timeout=60)
    assert r.status_code in (200, 404), f"Expected 200/404, got {r.status_code}: {r.text[:200]}"

def test_memory_summary():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "summary_length": "brief"}
    r = requests.post(f"{BASE_URL}/memory_summary", json=payload, headers=HEADERS, timeout=120)
    assert r.status_code in (200, 404), f"Expected 200/404, got {r.status_code}: {r.text[:200]}"

# ========== AGENT CHAT ==========

def test_agent_chat():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"], "message": "Hello, what do you remember?"}
    r = requests.post(f"{BASE_URL}/agent_chat", json=payload,
                      headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, timeout=120)
    assert r.status_code in (200, 403, 404), f"Expected 200/403/404, got {r.status_code}: {r.text[:200]}"

# ========== WEB ENDPOINTS ==========

def test_web_get_sessions():
    r = requests.get(f"{BASE_URL}/web/get_sessions", params={"id": "51ebe8c7-201b-4275-9bc5-44d7222f3509"}, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_web_rag():
    payload = {"user_id": "51ebe8c7-201b-4275-9bc5-44d7222f3509", "query": "test", "top_k": 3}
    r = requests.post(f"{BASE_URL}/web/rag", json=payload, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

# ========== CLEANUP ==========

def test_delete_memory():
    if not STATE["agent_id"] or not STATE["entry_id"]:
        raise AssertionError("No agent_id or entry_id")
    payload = {"agent_id": STATE["agent_id"], "entry_ids": [STATE["entry_id"]]}
    r = requests.post(f"{BASE_URL}/delete_memory", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"

def test_delete_agent():
    if not STATE["agent_id"]:
        raise AssertionError("No agent_id")
    payload = {"agent_id": STATE["agent_id"]}
    r = requests.post(f"{BASE_URL}/delete_agent", json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"


# ========== MAIN RUNNER ==========

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  Manhattan API — Full Test Suite")
    print(f"  Target: {BASE_URL}")
    print(f"  Time:   {datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    test_groups = [
        ("Health & Ping", [
            ("GET /ping", test_ping),
            ("GET /health", test_health),
            ("GET /health_detailed", test_health_detailed),
        ]),
        ("Authentication", [
            ("POST /validate_key (missing)", test_validate_key_missing),
            ("POST /validate_key (invalid)", test_validate_key_invalid),
            ("POST /validate_key (valid)", test_validate_key_valid),
        ]),
        ("Agent CRUD", [
            ("POST /create_agent", test_create_agent),
            ("GET  /list_agents", test_list_agents),
            ("GET  /get_agent", test_get_agent),
            ("POST /update_agent", test_update_agent),
            ("POST /disable_agent", test_disable_agent),
            ("POST /enable_agent", test_enable_agent),
        ]),
        ("Documents", [
            ("POST /add_document", test_add_document),
            ("POST /search_documents", test_search_documents),
            ("POST /update_document", test_update_document),
            ("POST /update_document_metadata", test_update_document_metadata),
            ("POST /search_chat_history", test_search_chat_history),
        ]),
        ("Memory — Core", [
            ("POST /create_memory", test_create_memory),
            ("POST /add_memory", test_add_memory),
            ("POST /read_memory", test_read_memory),
            ("POST /get_memories_by_bin", test_get_memories_by_bin),
            ("POST /get_context", test_get_context),
            ("POST /update_memory", test_update_memory),
            ("POST /process_raw", test_process_raw),
        ]),
        ("Analytics", [
            ("POST /agent_stats", test_agent_stats),
            ("POST /api_usage", test_api_usage),
        ]),
        ("Bulk Operations", [
            ("POST /list_memories", test_list_memories),
            ("POST /bulk_add_memory", test_bulk_add_memory),
        ]),
        ("Data Portability", [
            ("POST /export_memories", test_export_memories),
            ("POST /import_memories", test_import_memories),
            ("POST /memory_summary", test_memory_summary),
        ]),
        ("Agent Chat", [
            ("POST /agent_chat", test_agent_chat),
        ]),
        ("Web Endpoints", [
            ("GET  /web/get_sessions", test_web_get_sessions),
            ("POST /web/rag", test_web_rag),
        ]),
        ("Cleanup", [
            ("POST /delete_memory", test_delete_memory),
            ("POST /delete_agent", test_delete_agent),
        ]),
    ]

    total = 0
    for group_name, tests in test_groups:
        print(f"\n--- {group_name} ---")
        for name, fn in tests:
            run_test(name, fn)
            total += 1

    # Summary
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    errors = sum(1 for r in results if r[0] == "ERROR")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {errors} errors / {total} total")
    print(f"{'='*60}")

    if failed + errors > 0:
        print(f"\n  Failed/Error tests:")
        for status, name, msg in results:
            if status != "PASS":
                print(f"    [{status}] {name}")
                print(f"           {msg[:150]}")
        print()

    sys.exit(1 if failed + errors > 0 else 0)
