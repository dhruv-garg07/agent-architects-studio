# api_chats.py
import os, time, uuid
from flask import Blueprint, request, jsonify
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


def run_ai(message, history, session_id):
    # your model / tool-calling / RAG pipeline
    # This function should call LLM responses from the Response controller.
    return f"Echo This is the AI response: {message}"  # replace with real response

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

@api.post("/api/chat")               # (optional) generate + store assistant reply
def chat_and_store():
    data = request.get_json(force=True)
    thread_id = data.get("thread_id")
    user_id   = data.get("user_id")
    user_msg  = data["message"]
    history   = data.get("history", [])

    # 1) store the user message
    write_controller_chatH.send_data_to_rag_db(
        user_ID=user_id,
        content_data=user_msg,
        is_reply_to=None,
        message_type="human",
        conversation_thread=thread_id,
    )

    # 2) your AI generation (replace with your real function)
    reply_text = run_ai(user_msg, history, session_id=thread_id)

    # 3) store assistant message
    write_controller_chatH.send_data_to_rag_db(
        user_ID=user_id,
        content_data=reply_text,
        is_reply_to=None,   # or link to last user msg id if you track it
        message_type="llm",
        conversation_thread=thread_id,
    )

    return jsonify({"reply": reply_text})

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