# api_chats.py
import os, time, uuid, sys

sys.path.append(os.path.dirname(__file__))
# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Get the parent directory (one level up)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

# Add parent directory to sys.path
sys.path.insert(0, parent_dir)
print(parent_dir)

# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Go two levels up
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

# Add to sys.path
sys.path.insert(0, grandparent_dir)

# Now we have grandparent_dir, parent_dir, current_dir in sys.path.
# Can import anything from these directories.


from flask import Blueprint, request, jsonify, abort, Response
from LLM_calls.context_manager import query_llm_with_history, query_llm_with_history_stream
from LLM_calls.intelligent_query_rewritten import intelligent_query_rewriter
from LLM_calls.together_get_response import clean_response
from Octave_mem.RAG_DB_CONTROLLER.write_data_RAG import RAG_DB_Controller_CHAT_HISTORY
from Octave_mem.RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG
from Octave_mem.SqlDB.sqlDbController import add_message, get_chat_history_by_session
api = Blueprint("api", __name__)
import asyncio
import threading
from collections import deque
import json

import os
import sys
# import sys, os

# MessageType enum-like class for message roles
class MessageType:
    HUMAN = "human"
    LLM = "llm"
    NOTE = "note"

def run_ai(message, history, session_id, rag_context=None, chat_history=None):
    # your model / tool-calling / RAG pipeline
    # This function should call LLM responses from the Response controller.
    # If rag_context is provided, add it to the context for the LLM

    return query_llm_with_history_stream(message, history, rag_context, chat_history)  # replace with real response

# from LLM_calls use together_get_response functions for LLM calls.
# Make a orchestration function that calls the LLM and tools as needed.
# Context building from history and RAG retrieval should be done here.
# Use agents if needed. for example if you want to call a code interpreter tool or web search tool.
# Context building using Langchain memory modules can be done here.
# Example: use ConversationBufferMemory to build context from history.
# Use RAG retrieval to get relevant documents from Chroma DB.
# Structure of Context in tree diagram:
# Chat History ---------------> Context Builder ----------------> LLM/Agent/Tool Orchestration
# (ConversationBufferMemory)         (RAG Retrieval)               (LLM Calls, Tool Calls)
# (past messages)                   (Chroma DB)                   (user_id, thread_id)
# (user_id, thread_id)              (user_id, thread_id)          (message_id, content, role)
# (message_id, content, role)       (relevant docs)               (timestamp)
# (timestamp)                       (context)                     (is_reply_to)
# (is_reply_to)
# (conversation_thread) 
# (message_type)
# (note, human, llm)

# We should make a separate file for running AI controls.
# There should be Proper context building from the history and RAG retrieval.


write_controller_chatH = RAG_DB_Controller_CHAT_HISTORY(
    database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
)

# read_data_RAG contains both the functions of Chroma DB as well as supabase session mgmt for one given user_id.
read_controller_chatH = read_data_RAG(
    database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY")  # Use the same DB for reading   
)

read_controller_file_data = read_data_RAG(
    database=os.getenv("CHROMA_DATABASE_FILE_DATA")  # Use the same DB for reading   
)


# In-memory cache for chat histories to reduce SQLDB calls and scale for many requests.
# Structure: cache.store[user_id][session_id] -> deque of messages (maxlen=MAX_PER_SESSION)
class ChatHistoryCache:
    def __init__(self, max_per_session=30, max_sessions_per_user=200):
        self.max_per_session = max_per_session
        self.max_sessions_per_user = max_sessions_per_user
        self.store = {}  # user_id -> { session_id: deque([...]) }
        self.lock = threading.Lock()

    def get_session_history(self, user_id, session_id):
        with self.lock:
            return list(self.store.get(user_id, {}).get(session_id, []))

    def set_session_history(self, user_id, session_id, messages):
        # messages: list, we store oldest->newest
        with self.lock:
            user_map = self.store.setdefault(user_id, {})
            if len(user_map) >= self.max_sessions_per_user and session_id not in user_map:
                # evict oldest session (arbitrary) to keep memory bounded
                oldest = next(iter(user_map.keys()))
                user_map.pop(oldest, None)
            dq = deque(messages[-self.max_per_session:], maxlen=self.max_per_session)
            user_map[session_id] = dq

    def append_message(self, user_id, session_id, message):
        # message: dict, should be appended as newest
        with self.lock:
            user_map = self.store.setdefault(user_id, {})
            dq = user_map.get(session_id)
            if dq is None:
                dq = deque(maxlen=self.max_per_session)
                user_map[session_id] = dq
            dq.append(message)

    def preload_user_sessions(self, user_id, session_ids, fetcher_fn):
        # fetcher_fn(session_id, top_k) -> list(messages)
        # preload in background thread to avoid blocking
        def _preload():
            for sid in session_ids:
                try:
                    msgs = fetcher_fn(session_id=sid, top_k=self.max_per_session)
                    # store oldest->newest
                    self.set_session_history(user_id, sid, msgs)
                except Exception as e:
                    # ignore per-session failures
                    print(f"Preload error for {user_id}/{sid}: {e}")

        t = threading.Thread(target=_preload, daemon=True)
        t.start()


# instantiate global cache
chat_history_cache = ChatHistoryCache(max_per_session=30, max_sessions_per_user=400)

def _thread_id():
    return f"thread_{int(time.time())}"

# 1) List sessions for the user (to populate the left panel)
@api.get("/api/get_sessions")
def list_sessions():
    id = request.args.get("id")
    print("Query ID:", id)
    session_ids = asyncio.run(read_controller_chatH.list_session_ids(id=id))   
    print(f"Session IDs for {id}: {session_ids}")
    # TODO: implement real Chroma query that lists the user's threads
    # Return newest-first. Shape: [{"thread_id": "...", "createdAt": "...", "updatedAt": "...", "preview": "last msg"}]
    # Kick off a background preload of the last N messages for each session so the UI can load immediately
    try:
        ids = [s if isinstance(s, str) else s.get('id') or s.get('thread_id') for s in session_ids]
        # fall back to native shape if the controller already returned objects
        ids = [i for i in ids if i]
        # use SQL fetcher function wrapper
        def _fetcher(session_id, top_k=30):
            # Use existing SQL DB controller to fetch most recent messages (descending or as implemented)
            return get_chat_history_by_session(user_id=id, session_id=session_id, top_k=top_k)

        # Preload in background via cache
        chat_history_cache.preload_user_sessions(user_id=id, session_ids=ids, fetcher_fn=_fetcher)
    except Exception as e:
        print(f"Preload scheduling failed: {e}")

    return session_ids

@api.post("/api/create_session")
def create_session():
    user_id = (request.get_json() or {}).get("user_id")
    thread_id = str(uuid.uuid4())
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Optional: write a session metadata row into Chroma/your store
    thread_id_created = asyncio.run(read_controller_chatH.create_session(id=user_id, thread_id=thread_id, created=created))
    # (Or infer sessions solely from messages later.)
    return jsonify({"thread_id": thread_id_created, "createdAt": created})


@api.get("/api/sessions/<thread_id>/messages")  # load history for a thread
def get_messages(thread_id):
    id = request.args.get("id")
    print(f"Loading messages for user {id} in thread {thread_id}")
    # First try serving from cache to avoid SQLDB hits
    try:
        cached = chat_history_cache.get_session_history(user_id=id, session_id=thread_id)
        if cached and len(cached) > 0:
            return jsonify({"messages": cached})
    except Exception as e:
        print(f"Cache read error: {e}")

    # fallback to SQL DB read
    messages = get_chat_history_by_session(user_id=id, session_id=thread_id, top_k=100)

    # store into cache for future requests (truncate to cache size)
    try:
        chat_history_cache.set_session_history(user_id=id, session_id=thread_id, messages=messages)
    except Exception as e:
        print(f"Cache set error: {e}")

    return jsonify({"messages": messages})



# @api.post("/api/messages")           # store ONE message
# def store_message():
#     data = request.get_json(force=True)
#     user_id    = data.get("user_id", "user123")
#     content    = data["content"]
#     role       = data["role"]            # "human" | "llm"
#     thread_id  = data["thread_id"]
#     reply_to   = data.get("is_reply_to") # optional int or message_id

#     # write into Chroma
#     result = write_controller_chatH.send_data_to_rag_db(
#         user_ID=user_id,
#         content_data=content,
#         is_reply_to=reply_to,
#         message_type="llm" if role == "llm" else "human",
#         conversation_thread=thread_id,
#     )
#     return jsonify({"ok": True, "result": result})

def split_text_into_chunks(text, max_sentences=4, overlap=1):
    import re
    # Split text into sentences (simple split, can be improved)
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    i = 0
    while i < len(sentences):
        chunk = sentences[i:i+max_sentences]
        if chunk:
            chunks.append(' '.join(chunk))
        if i + max_sentences >= len(sentences):
            break
        i += max_sentences - overlap
    return chunks

@api.post("/api/chat")
def chat_and_store():
    print("On Clicking send button in chat UI...")
    import time, re
    data      = request.get_json(force=True)
    thread_id = data["thread_id"]
    user_id   = data["user_id"]
    user_msg  = data["message"]
    history   = data.get("history", [])
    top_k     = 20
    t0        = time.time()

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())
    

    raw_rows = read_controller_chatH.fetch_related_to_query(
        user_ID=user_id, query=f"query: {user_msg}", top_k=top_k
    )
    raw_rows_file_data = read_controller_file_data.fetch_related_to_query(
        user_ID=user_id, query=f"query: {user_msg}", top_k=top_k
    )
    raw_rows.extend(raw_rows_file_data)
    rewritten_user_msg = intelligent_query_rewriter(user_msg, raw_rows) 
    # print(f"Rewritten user msg: {rewritten_user_msg}")

    # 1) RAG FIRST (so it can't see this very message)
    raw_rows = read_controller_chatH.fetch_related_to_query(
        user_ID=user_id, query=f"{rewritten_user_msg} query: {user_msg}", top_k=top_k
    )
    
    # Based on the query it should tell whether to fetch from file_data DB or not:
    
    # Also fetch from file_data DB
    raw_rows_file_data = read_controller_file_data.fetch_related_to_query(
        user_ID=user_id, query=f"{rewritten_user_msg} query: {user_msg}", top_k=top_k
    )
    raw_rows.extend(raw_rows_file_data)
    



    # drop anything that is basically the same text as the query (belt & suspenders)
    qn = _norm(rewritten_user_msg)
    raw_rows = [r for r in raw_rows if _norm(r.get("document") or "") != qn]

    # normalize -> UI shape
    q_terms = [t.lower() for t in rewritten_user_msg.split() if len(t) > 2]
    rag_results = _normalize_rag_rows(raw_rows, q_terms)  # uses _to_score & _epoch_to_human as before

    # print("raw_rows:", raw_rows)
    
    # Retrieve the old chat history from cache (fallback to SQL DB) for context
    chat_history = chat_history_cache.get_session_history(user_id=user_id, session_id=thread_id)
    if not chat_history:
        # fallback to SQL DB and populate cache
        chat_history = get_chat_history_by_session(user_id=user_id, session_id=thread_id, top_k=20)
        try:
            chat_history_cache.set_session_history(user_id=user_id, session_id=thread_id, messages=chat_history)
        except Exception as e:
            print(f"Cache set error during chat: {e}")
    
    # 2) generate reply generator using RAG context (streaming)
    reply_generator = run_ai(f"{rewritten_user_msg} query: {user_msg}", history, session_id=thread_id, rag_context=raw_rows, chat_history=chat_history)
    
    # 3) Store messages in background using threads (will be called after streaming completes)
    def store_messages_background(full_text):
        """Store messages in background after streaming completes"""
        try:
            # Store user message chunks
            add_message(user_id, MessageType.HUMAN, user_msg, session_id=thread_id)
            # update cache with the optimistic user message (so UI will reflect immediately on reload)
            try:
                chat_history_cache.append_message(user_id=user_id, session_id=thread_id, message={
                    "role": "user",
                    "content": user_msg,
                    "timestamp": int(time.time())
                })
            except Exception:
                pass
            for chunk in split_text_into_chunks(user_msg, max_sentences=4, overlap=1):
                write_controller_chatH.send_data_to_rag_db(
                    user_ID=user_id,
                    content_data=chunk,
                    is_reply_to=None,
                    message_type=MessageType.HUMAN,
                    conversation_thread=thread_id,
                )
            # Store reply chunks
            add_message(user_id, MessageType.LLM, full_text, session_id=thread_id)
            # update cache with AI reply
            try:
                chat_history_cache.append_message(user_id=user_id, session_id=thread_id, message={
                    "role": "assistant",
                    "content": full_text,
                    "timestamp": int(time.time())
                })
            except Exception:
                pass
            for chunk in split_text_into_chunks(full_text, max_sentences=4, overlap=1):
                write_controller_chatH.send_data_to_rag_db(
                    user_ID=user_id,
                    content_data=chunk,
                    is_reply_to=None,
                    message_type=MessageType.LLM,
                    conversation_thread=thread_id,
                )
        except Exception as e:
            print(f"Error in background storage: {str(e)}")
    
    # Collect full response while streaming to frontend
    full_reply_text = ""
    
    def generate_streaming_response():
        """Generator function that yields SSE-formatted data with tokens and final metadata"""
        nonlocal full_reply_text
        
        print(f"[STREAM] Starting to stream response for user {user_id} in session {thread_id}")
        
        try:
            # Stream tokens from the LLM
            token_count = 0
            for token in reply_generator:
                token_count += 1
                full_reply_text += token
                print(f"[STREAM] Token {token_count}: {repr(token)}", flush=True)
                # Send token as Server-Sent Event (escape JSON properly)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            print(f"[STREAM] All tokens received. Total: {token_count}. Full response length: {len(full_reply_text)}", flush=True)
            print(f"[STREAM] Full text preview: {repr(full_reply_text[:300])}...", flush=True)
            
            # FINAL SAFETY CLEANUP - remove any markers that may have slipped through
            cleaned_response = clean_response(full_reply_text)
            print(f"[STREAM] Cleaned response length: {len(cleaned_response)}", flush=True)
            
            # Verification: ensure no markers remain
            if "<|end|>" in cleaned_response or "[END FINAL RESPONSE]" in cleaned_response:
                print(f"[STREAM] ⚠️  WARNING: Markers still present in cleaned response!", flush=True)
                # Force cleanup one more time
                cleaned_response = cleaned_response.replace("<|end|>", "").replace("[END FINAL RESPONSE]", "").strip()
                print(f"[STREAM] Force-cleaned length: {len(cleaned_response)}", flush=True)
            else:
                print(f"[STREAM] ✓ Markers verified removed from response", flush=True)
            
            # After streaming completes, send RAG results and completion signal
            yield f"data: {json.dumps({'type': 'rag_results', 'content': rag_results})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'full_response': cleaned_response})}\n\n"
            
            print(f"[STREAM] Yielded RAG results and done signal")
            
            # Start background storage thread after streaming is complete (use cleaned response)
            from threading import Thread
            thread = Thread(target=store_messages_background, args=(cleaned_response,))
            thread.daemon = True
            thread.start()
            print(f"[STREAM] Started background storage thread")
            
        except Exception as e:
            print(f"[STREAM] Error during streaming: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    # Return streaming response with SSE content type
    return Response(generate_streaming_response(), mimetype='text/event-stream')

@api.post("/api/notes")
def store_note():
    d = request.get_json(force=True)
    return jsonify(write_controller_chatH.send_data_to_rag_db(
        user_ID=d.get("user_id","user123"),
        content_data=d["text"],
        is_reply_to=None,
        message_type=MessageType.NOTE,
        conversation_thread=d["thread_id"]
    ))

# Create HTML for new session
# Update the function here to get the messages from the RAG DB
def _epoch_to_human(ts):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(ts)))
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

@api.post("/api/rag")
def rag_search():
    data = request.get_json(force=True) or {}
    user_id   = data.get("user_id")
    query     = (data.get("query") or "").strip()
    thread_id = data.get("thread_id")  # optional
    top_k     = int(data.get("top_k", 5))

    if not user_id or not query:
        abort(400, "Missing user_id or query")

    rows = read_controller_chatH.fetch_related_to_query(
        user_ID=user_id,
        query=query,
        top_k=top_k
    )

    # Optional filter to current thread
    if thread_id:
        rows = [r for r in rows if (r.get("metadata") or {}).get("conversation_thread") == thread_id]

    # distance -> score (monotonic): lower distance => higher score
    def to_score(d):
        try:
            return 1.0 / (1.0 + float(d))
        except Exception:
            return 0.0

    # build UI results
    q_terms = [t.lower() for t in query.split() if len(t) > 2]
    results = []
    for i, r in enumerate(rows):
        meta = r.get("metadata", {})
        results.append({
            "id": r.get("id") or f"res_{i+1}",
            "score": to_score(r.get("distance")),
            "text": r.get("document") or "",
            "source": meta.get("source") or "chat_session",
            "timestamp": _epoch_to_human(meta.get("timestamp")),
            "matches": q_terms,  # your frontend will highlight these
        })

    # sort by score desc
    results.sort(key=lambda x: x["score"], reverse=True)

    return jsonify({"results": results})

@api.post("/api/rag/feedback")
def rag_feedback():
    d = request.get_json(force=True)
    # d: {user_id, thread_id, result_id, rating}
    # persist feedback somewhere (e.g., a table or Chroma metadata)
    return jsonify({"ok": True})

# api.py
def _epoch_to_human(ts):
    import time
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(ts)))
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

def _to_score(distance):
    try:
        return 1.0 / (1.0 + float(distance))  # lower distance => higher score
    except Exception:
        return 0.0

def _normalize_rag_rows(rows, query_terms):
    results = []
    for i, r in enumerate(rows or []):
        meta = r.get("metadata", {})
        results.append({
            "id": r.get("id") or f"res_{i+1}",
            "score": _to_score(r.get("distance")),
            "text": r.get("document") or "",
            "source": meta.get("source") or "chat_session",
            "timestamp": _epoch_to_human(meta.get("timestamp")),
            "matches": query_terms,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


