import requests
import json
import time

# Simple validation tests for the running server at the provided base URL.
# These are pytest-compatible functions but can also be executed directly via `python api_test.py`.

BASE_URL = "https://themanhattanproject.ai"


def test_memory_get():
    """GET /memory should return an OK page (200) or redirect to login (302).
    The test asserts a 200 response; adjust if your server uses redirects for unauthenticated users.
    """
    s = requests.Session()
    r = s.get(f"{BASE_URL}/memory", allow_redirects=True, timeout=15)
    assert r.status_code == 200, f"Unexpected status for /memory: {r.status_code}\nResponse snippet: {r.text[:300]}"


def test_get_sessions_api():
    """Call GET /api/get_sessions?id=... and expect a JSON response (list or dict).
    If your API requires authentication, this may return 401/403.
    """
    r = requests.get(f"{BASE_URL}/web/get_sessions", params={"id": "51ebe8c7-201b-4275-9bc5-44d7222f3509"}, timeout=15)
    assert r.status_code == 200, f"GET /api/get_sessions returned {r.status_code}: {r.text[:300]}"
    try:
        data = r.json()
    except Exception as e:
        raise AssertionError(f"/api/get_sessions did not return valid JSON: {e}\n{text_preview(r.text)}")
    assert isinstance(data, (list, dict)), f"Unexpected JSON shape for /api/get_sessions: {type(data)}"


def test_rag_search_api():
    """POST /api/rag with a minimal payload and expect a JSON response containing 'results'.
    """
    payload = {"user_id": "51ebe8c7-201b-4275-9bc5-44d7222f3509", "query": "test query", "top_k": 3}
    r = requests.post(f"{BASE_URL}/web/rag", json=payload, timeout=15)
    assert r.status_code == 200, f"POST /api/rag returned {r.status_code}: {r.text[:300]}"
    try:
        data = r.json()
    except Exception as e:
        raise AssertionError(f"/api/rag did not return valid JSON: {e}\n{text_preview(r.text)}")
    assert "results" in data, f"/api/rag JSON missing 'results' key: {data.keys()}"
    assert isinstance(data["results"], list), f"Expected 'results' to be a list, got {type(data['results'])}"


def create_session(user_id: str) -> str:
    """Create a new chat session via /api/create_session and return thread_id.
    Falls back to a generated UUID-like value if the API call fails.
    """
    try:
        r = requests.post(f"{BASE_URL}/web/create_session", json={"user_id": user_id}, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("thread_id") or data.get("thread_id_created") or data.get("thread_id_created")
    except Exception:
        # fallback to a simple timestamp-based id
        return f"local_thread_{int(time.time())}"


def interactive_chat():
    """Interactive CLI that sends messages to /api/chat and prints streaming SSE responses.
    Works with the server's SSE format (data: <json> lines) used in api_chats.chat_and_store.
    """
    user_id = input("User ID (press enter to use example id): ").strip() or "51ebe8c7-201b-4275-9bc5-44d7222f3509"
    print(f"Using user_id: {user_id}\n")

    create = input("Create a new session? (Y/n): ").strip().lower() or "y"
    if create in ("y", "yes"):
        thread_id = create_session(user_id)
        print(f"Created/using thread_id: {thread_id}\n")
    else:
        thread_id = input("Enter existing thread_id: ").strip()

    print("Type your message and press Enter. Empty message exits.\n")

    while True:
        try:
            user_msg = input("You: ").strip()
        except EOFError:
            break
        if not user_msg:
            print("Exiting interactive chat.")
            break

        payload = {
            "thread_id": thread_id,
            "user_id": user_id,
            "message": user_msg,
            "history": []
        }

        print("Sending message, streaming response...\n")
        try:
            with requests.post(f"{BASE_URL}/web/chat", json=payload, stream=True, timeout=120) as resp:
                resp.raise_for_status()

                full_reply = ""
                # iterate over streaming lines
                for raw_line in resp.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    # SSE lines are typically prefixed with 'data: '
                    if line.startswith("data:"):
                        json_part = line[len("data:"):].strip()
                        try:
                            ev = json.loads(json_part)
                        except Exception:
                            # not JSON -> print raw
                            print(json_part)
                            continue

                        etype = ev.get("type")
                        if etype == "token":
                            token = ev.get("content", "")
                            print(token, end="", flush=True)
                            full_reply += token
                        elif etype == "rag_results":
                            print("\n\n[RAG results]:")
                            print(json.dumps(ev.get("content"), indent=2))
                            print("\n")
                        elif etype == "done":
                            # done may contain the full_response
                            final = ev.get("full_response") or ev.get("content")
                            if final is None:
                                final = ""
                            # If the streaming already printed tokens, just print newline then the final summary
                            print("\n\n[Done] Final response:\n")
                            print(final)
                            full_reply = final
                            break
                        elif etype == "error":
                            print("\n\n[Error from server]:", ev.get("content"))
                            break
                        else:
                            # Unknown event types
                            print("\n[Event]:", ev)

                print("\n--- End of response ---\n")

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


# Helper used in error messages

def text_preview(s: str, length: int = 300) -> str:
    try:
        return (s or "")[:length]
    except Exception:
        return "<unavailable>"


if __name__ == "__main__":
    # If user wants interactive chat, run it; otherwise run the basic tests
    mode = input("Run interactive chat or tests? (chat/tests) [chat]: ").strip().lower() or "chat"
    if mode.startswith("chat"):
        interactive_chat()
    else:
        # Run tests manually and print brief success/failure
        tests = [test_memory_get, test_get_sessions_api, test_rag_search_api]
        for t in tests:
            try:
                print(f"Running {t.__name__}()...")
                t()
                print(f"{t.__name__}: OK\n")
            except AssertionError as ae:
                print(f"{t.__name__}: FAILED - {ae}\n")
                
            except Exception as e:
                print(f"{t.__name__}: ERROR - {e}\n")