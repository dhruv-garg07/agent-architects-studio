# api_chats.py
import os, time, uuid
from flask import Blueprint, request, jsonify, abort
from LLM_calls.context_manager import query_llm_with_history
from LLM_calls.intelligent_query_rewritten import intelligent_query_rewriter
from Octave_mem.RAG_DB_CONTROLLER.write_data_RAG import RAG_DB_Controller_CHAT_HISTORY
from Octave_mem.RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG
api = Blueprint("api", __name__)
import asyncio

import os
import sys
# import sys, os
sys.path.append(os.path.dirname(__file__))
# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Get the parent directory (one level up)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

# Add parent directory to sys.path
sys.path.insert(0, parent_dir)
print(parent_dir)
import sys
import os

# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Go two levels up
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

# Add to sys.path
sys.path.insert(0, grandparent_dir)

# Now we have grandparent_dir, parent_dir, current_dir in sys.path.
# Can import anything from these directories.


def run_ai(message, history, session_id, rag_context=None):
    # your model / tool-calling / RAG pipeline
    # This function should call LLM responses from the Response controller.
    # If rag_context is provided, add it to the context for the LLM

    return query_llm_with_history(message, history, rag_context)  # replace with real response

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
# (past messages)                   (Chroma DB)                   (Response generation)
# (user_id, thread_id)              (user_id, thread_id)          (user_id, thread_id)
# (message_id, content, role)       (relevant docs)               (final response)
# (timestamp)                       (context)                     (tool calls)
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
    # implement a real read from Chroma if you have it;
    # otherwise return [] and keep local cache for now
    messages = read_controller_chatH.fetch_by_conversation_thread(user_id=id, conversation_thread=thread_id, top_k=100)
    print(messages)
    return jsonify({"messages": messages})

@api.post("/api/messages")           # store ONE message
def store_message():
    data = request.get_json(force=True)
    user_id    = data.get("user_id", "user123")
    content    = data["content"]
    role       = data["role"]            # "human" | "llm"
    thread_id  = data["thread_id"]
    reply_to   = data.get("is_reply_to") # optional int or message_id

    # write into Chroma
    result = write_controller_chatH.send_data_to_rag_db(
        user_ID=user_id,
        content_data=content,
        is_reply_to=reply_to,
        message_type="llm" if role == "llm" else "human",
        conversation_thread=thread_id,
    )
    return jsonify({"ok": True, "result": result})

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
    import time, re
    data      = request.get_json(force=True)
    thread_id = data["thread_id"]
    user_id   = data["user_id"]
    user_msg  = data["message"]
    history   = data.get("history", [])
    top_k     = 3
    t0        = time.time()

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    rewritten_user_msg = intelligent_query_rewriter(user_msg) 
    print(f"Rewritten user msg: {rewritten_user_msg}")

    # 1) RAG FIRST (so it can't see this very message)
    raw_rows = read_controller_chatH.fetch_related_to_query(
        user_ID=user_id, query=f"{rewritten_user_msg} query: {user_msg}", top_k=top_k
    )
    
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
    
    # 2) generate reply using RAG context
    reply_text = run_ai(f"{rewritten_user_msg} query: {user_msg}", history, session_id=thread_id, rag_context=raw_rows)

    # 3) NOW store the user message (after RAG) and then the reply
    for chunk in split_text_into_chunks(user_msg, max_sentences=4, overlap=1):
        write_controller_chatH.send_data_to_rag_db(
            user_ID=user_id,
            content_data=chunk,
            is_reply_to=None,
            message_type="human",
            conversation_thread=thread_id,
        )

    for chunk in split_text_into_chunks(reply_text, max_sentences=4, overlap=1):
        write_controller_chatH.send_data_to_rag_db(
            user_ID=user_id,
            content_data=chunk,
            is_reply_to=None,
            message_type="llm",
            conversation_thread=thread_id,
        )

    return jsonify({"reply": reply_text, "rag_results": rag_results})

@api.post("/api/notes")
def store_note():
    d = request.get_json(force=True)
    return jsonify(write_controller_chatH.send_data_to_rag_db(
        user_ID=d.get("user_id","user123"),
        content_data=d["text"],
        is_reply_to=None,
        message_type="note",
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
