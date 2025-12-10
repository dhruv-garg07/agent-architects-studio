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
from LLM_calls.intelligent_query_rewritten import intelligent_query_rewriter, LLMEnhancedRewriter
from LLM_calls.together_get_response import clean_response
from Octave_mem.RAG_DB_CONTROLLER.write_data_RAG import RAG_DB_Controller_CHAT_HISTORY
from Octave_mem.RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG
from Octave_mem.SqlDB.sqlDbController import add_message, get_chat_history_by_session
api = Blueprint("api", __name__)
import asyncio
import threading
from collections import deque
import json
llm_enchanced_query_rewriter = LLMEnhancedRewriter()
import os
import sys
# import sys, os

# MessageType enum-like class for message roles
class MessageType:
    HUMAN = "human"
    LLM = "llm"
    NOTE = "note"

def run_ai(
        message,
        session_id,
        rag_context,
        chat_history,
        system_prompt,
        temperature=0.3
    ):
    # your model / tool-calling / RAG pipeline
    # This function should call LLM responses from the Response controller.
    # If rag_context is provided, add it to the context for the LLM

    return query_llm_with_history_stream(message, rag_context, chat_history, system_prompt, temperature)  # replace with real response

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

import time, re
from typing import List, Dict, Any
from collections import defaultdict
import hashlib
@api.post("/api/chat")
def chat_and_store():
    print("🟢 Chat endpoint triggered...")
    
    
    data = request.get_json(force=True)
    thread_id = data["thread_id"]
    user_id = data["user_id"]
    user_msg = data["message"].strip()
    use_file_rag = data.get("use_file_rag", False)
    conversation_mode = data.get("mode", "balanced")  # balanced, precise, creative
    
    # Adaptive top_k based on mode
    top_k_config = {
        "precise": {"chat": 5, "file": 3},
        "balanced": {"chat": 8, "file": 7},
        "creative": {"chat": 10, "file": 10}
    }
    
    top_k = top_k_config.get(conversation_mode, top_k_config["balanced"])
    t0 = time.time()

    print(f"[RAG] File RAG: {use_file_rag} | Mode: {conversation_mode} | Top-K: {top_k}")

    # ==================== UTILITY FUNCTIONS ====================
    def _normalize_text(text: Any) -> str:
        """Enhanced text normalization with semantic preservation"""
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
        
        # Preserve important markers before normalization
        preserved_markers = {
            'Q:': ' __QUESTION__ ',
            'A:': ' __ANSWER__ ',
            '```': ' __CODE_BLOCK__ ',
            '$$': ' __MATH__ ',
            'http://': ' __URL__ ',
            'https://': ' __URL__ '
        }
        
        for marker, placeholder in preserved_markers.items():
            text = text.replace(marker, placeholder)
        
        # Normalize
        text = re.sub(r"\s+", " ", text.strip().lower())
        
        # Restore markers
        for marker, placeholder in preserved_markers.items():
            text = text.replace(placeholder, marker)
        
        return text
    
    def _calculate_relevance_score(query: str, document: str) -> float:
        """Calculate semantic relevance score between query and document"""
        query_terms = set(_normalize_text(query).split())
        doc_terms = set(_normalize_text(document).split())
        
        if not query_terms or not doc_terms:
            return 0.0
        
        # Jaccard similarity
        intersection = query_terms.intersection(doc_terms)
        union = query_terms.union(doc_terms)
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Boost for consecutive term matches
        consecutive_boost = 0.0
        query_lower = query.lower()
        doc_lower = document.lower()
        
        # Check for multi-word phrase matches
        for i in range(len(query_terms)):
            terms_list = list(query_terms)
            if i + 2 < len(terms_list):
                phrase = ' '.join(terms_list[i:i+3])
                if phrase in doc_lower:
                    consecutive_boost += 0.3
        
        # Final score (Jaccard + boost, capped at 1.0)
        return min(1.0, jaccard + consecutive_boost * 0.1)
    
    def _deduplicate_rag_results(results: List[Dict], threshold: float = 0.85) -> List[Dict]:
        """Remove near-duplicate RAG results based on content similarity"""
        unique_results = []
        seen_hashes = set()
        
        for result in results:
            content = result.get("document", "")
            content_hash = hashlib.md5(_normalize_text(content).encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
            else:
                # Check if this is a better version (more metadata, higher score)
                for idx, existing in enumerate(unique_results):
                    existing_hash = hashlib.md5(_normalize_text(existing.get("document", "")).encode()).hexdigest()
                    if content_hash == existing_hash:
                        if result.get("score", 0) > existing.get("score", 0):
                            unique_results[idx] = result
                        break
        
        return unique_results
    
    # ==================== STAGE 1: INITIAL RAG RETRIEVAL ====================
    print("#1️⃣ Initial RAG Retrieval")
    
    # Fetch from chat history
    print(f"  ↳ Fetching chat history (top_k={top_k['chat']})...")
    chat_rows = read_controller_chatH.fetch_related_to_query(
        user_ID=user_id,
        query=user_msg,
        top_k=top_k['chat']
    )
    
    # Fetch from file data if enabled
    file_rows = []
    if use_file_rag:
        print(f"  ↳ Fetching file data (top_k={top_k['file']})...")
        file_rows = read_controller_file_data.fetch_related_to_query(
            user_ID=user_id,
            query=user_msg,
            top_k=top_k['file']
        )
    
    all_rows = chat_rows + file_rows
    
    # Score and sort initial results
    for row in all_rows:
        row["relevance_score"] = _calculate_relevance_score(user_msg, row.get("document", ""))
    
    all_rows.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    print(f"  ↳ Found {len(chat_rows)} chat results, {len(file_rows)} file results")
    print(f"  ↳ Top relevance scores: {[r.get('relevance_score', 0) for r in all_rows[:3]]}")
    
    # ==================== STAGE 2: QUERY REWRITING ====================
    print("#2️⃣ Query Rewriting")
    
    # Extract key concepts from top results for better query expansion
    key_concepts = []
    for row in all_rows[:5]:  # Use top 5 results
        doc = row.get("document", "")
        # Extract potential key phrases (capitalized terms, technical terms)
        terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', doc)
        key_concepts.extend(terms[:3])  # Take first 3 terms
    
    # Remove duplicates and limit
    key_concepts = list(dict.fromkeys(key_concepts))[:5]
    
    # Intelligent query rewriting with context
    context_for_rewriter = "\n".join([r.get("document", "")[:200] for r in all_rows[:3]])
    print(f"  ↳ Context for rewriter: '{context_for_rewriter[:100]}...'")
    print(f"  ↳ Key concepts identified: {key_concepts}")
    
    # rewritten = intelligent_query_rewriter(
    #     original_query="How does it work?",
    #     context=context_for_rewriter,
    #     # key_concepts=["backpropagation", "gradient descent", "activation functions"],
    #     mode="precise",
    #     rag_context=file_rows,
    #     chat_history=chat_rows
    # )
    
    rewritten = llm_enchanced_query_rewriter.rewrite_with_llm(query=user_msg,context=all_rows,mode=conversation_mode)
    rewritten_user_msg = rewritten
    
    print(f"  ↳ Rewritten query: '{rewritten_user_msg}'")
    
    # ==================== STAGE 3: ENHANCED RAG RETRIEVAL ====================
    print("#3️⃣ Enhanced RAG Retrieval")
    
    # Create hybrid query (original + rewritten + key concepts)
    hybrid_query = f"{user_msg} {rewritten_user_msg} {' '.join(key_concepts)}"
    hybrid_query = ' '.join(dict.fromkeys(hybrid_query.split()))  # Remove duplicate words
    
    print(f"  ↳ Hybrid query: '{hybrid_query[:100]}...'")
    
    # Fetch with hybrid query
    enhanced_chat_rows = read_controller_chatH.fetch_related_to_query(
        user_ID=user_id,
        query=hybrid_query,
        top_k=top_k['chat'] // 2  # More focused retrieval
    )
    
    enhanced_file_rows = []
    if use_file_rag:
        enhanced_file_rows = read_controller_file_data.fetch_related_to_query(
            user_ID=user_id,
            query=hybrid_query,
            top_k=top_k['file'] // 2
        )
    
    enhanced_rows = enhanced_chat_rows + enhanced_file_rows
    
    # Score enhanced results
    for row in enhanced_rows:
        row["relevance_score"] = _calculate_relevance_score(hybrid_query, row.get("document", ""))
        row["source"] = "enhanced"
    
    # Mark original rows
    for row in all_rows:
        row["source"] = "initial"
    
    # Combine and deduplicate
    combined_rows = enhanced_rows + all_rows
    combined_rows = _deduplicate_rag_results(combined_rows)
    
    # Re-score all combined results with the hybrid query
    for row in combined_rows:
        row["final_score"] = _calculate_relevance_score(hybrid_query, row.get("document", "")) * 0.7 + \
                            row.get("relevance_score", 0) * 0.3
    
    # Sort by final score
    combined_rows.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    
    # Select top results based on conversation mode
    if conversation_mode == "precise":
        final_rows = combined_rows[:8]
    elif conversation_mode == "creative":
        final_rows = combined_rows[:15]
    else:  # balanced
        final_rows = combined_rows[:12]
    
    print(f"  ↳ Selected {len(final_rows)} final results for context")
    
    # ==================== STAGE 4: QUERY-DOCUMENT FILTERING ====================
    print("#4️⃣ Query-Document Filtering")
    
    # Remove results too similar to the query (avoid circular reference)
    qn = _normalize_text(rewritten_user_msg)
    filtered_rows = []
    
    for row in final_rows:
        doc_norm = _normalize_text(row.get("document", ""))
        
        # Calculate similarity to query
        query_terms = set(qn.split())
        doc_terms = set(doc_norm.split())
        intersection = query_terms.intersection(doc_terms)
        
        # Only filter if document is VERY similar to query (>90% overlap)
        if len(intersection) / len(query_terms) < 0.9 and doc_norm != qn:
            filtered_rows.append(row)
        else:
            print(f"  ↳ Filtered out near-identical document: {doc_norm[:50]}...")
    
    final_rows = filtered_rows
    
    # ==================== STAGE 5: CHAT HISTORY RETRIEVAL ====================
    print("#5️⃣ Chat History Context")
    
    # Get recent chat history with smart windowing
    chat_history = chat_history_cache.get_session_history(
        user_id=user_id, 
        session_id=thread_id
    )
    
    if not chat_history:
        # Adaptive history retrieval based on query complexity
        query_length = len(user_msg.split())
        history_top_k = min(20, max(10, query_length * 2))
        
        chat_history = get_chat_history_by_session(
            user_id=user_id,
            session_id=thread_id,
            top_k=history_top_k
        )
        
        # Cache for future use
        try:
            chat_history_cache.set_session_history(
                user_id=user_id,
                session_id=thread_id,
                messages=chat_history
            )
        except Exception as e:
            print(f"  ↳ Cache error: {e}")
    
    # Filter chat history to most relevant exchanges
    if len(chat_history) > 10:
        # Keep last 5 exchanges + any that mention key concepts
        recent_history = chat_history[-10:]  # Last 5 exchanges (10 messages)
        
        # Find history mentioning key concepts
        concept_history = []
        for i in range(0, len(chat_history) - 1, 2):  # Process as Q-A pairs
            if i + 1 < len(chat_history):
                q = chat_history[i].get("content", "")
                a = chat_history[i + 1].get("content", "")
                
                # Check if contains key concepts
                for concept in key_concepts:
                    if concept.lower() in q.lower() or concept.lower() in a.lower():
                        concept_history.extend([chat_history[i], chat_history[i + 1]])
                        break
        
        # Combine, deduplicate, and limit
        combined_history = recent_history + concept_history
        seen = set()
        unique_history = []
        
        for msg in combined_history:
            msg_hash = hashlib.md5(msg.get("content", "").encode()).hexdigest()
            if msg_hash not in seen:
                seen.add(msg_hash)
                unique_history.append(msg)
        
        chat_history = unique_history[-20:]  # Max 20 messages
    
    print(f"  ↳ Retrieved {len(chat_history)} chat history messages")
    
    # ==================== STAGE 6: CONTEXT ASSEMBLY ====================
    print("#6️⃣ Context Assembly")
    
    # Prepare RAG context with metadata
    rag_context = []
    for i, row in enumerate(final_rows[:8]):  # Use top 8 for context
        context_item = {
            "id": row.get("id", f"ctx_{i}"),
            "content": row.get("document", ""),
            "score": row.get("final_score", 0),
            "source": row.get("source", "unknown"),
            "metadata": row.get("metadata", {})
        }
        rag_context.append(context_item)
    
    # Prepare system prompt based on mode and RAG availability
    if use_file_rag and rag_context:
        if conversation_mode == "precise":
            system_prompt = "You are a precise assistant. Use the provided documents to give accurate, factual answers. Cite specific information when possible."
        elif conversation_mode == "creative":
            system_prompt = "You are a creative assistant. Synthesize information from the provided documents to generate insightful, expansive answers."
        else:
            system_prompt = "You are a helpful assistant. Use the provided context to answer questions accurately and comprehensively."
    else:
        system_prompt = "You are a helpful assistant. Answer based on your knowledge and the conversation history."
    
                # After streaming completes, send RAG results and completion signal
    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip().lower())
    
    qn = _norm(rewritten_user_msg)
    all_rows = [r for r in all_rows if _norm(r.get("document") or "") != qn]

    # normalize -> UI shape
    q_terms = [t.lower() for t in rewritten_user_msg.split() if len(t) > 2]
    rag_results = _normalize_rag_rows(all_rows, q_terms)  # uses _to_score & _epoch_to_human as before
    
    # ==================== STAGE 7: LLM GENERATION ====================
    print("#7️⃣ LLM Generation")
    
    # Prepare final query with context indicators
    final_query = f"Query: {user_msg}"
    if rewritten_user_msg != user_msg:
        final_query += f" (interpreted as: {rewritten_user_msg})"
    
    # Include key concepts in query if they add value
    if key_concepts:
        final_query += f" [Key concepts: {', '.join(key_concepts[:3])}]"
    
    print(f"  ↳ Final query to LLM: '{final_query[:100]}...'")
    print(f"  ↳ Context: {len(rag_context)} RAG items, {len(chat_history)} history messages")
    print(f"  ↳ Total processing time: {time.time() - t0:.2f}s")
    
    # Generate response
    reply_generator = run_ai(
        message=final_query,
        session_id=thread_id,
        rag_context=rag_context,
        chat_history=chat_history,
        system_prompt=system_prompt,
        temperature=0.7 if conversation_mode == "creative" else 0.3
    )
    
    # return Response(reply_generator, mimetype="text/event-stream")
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
                # print(f"[STREAM] Token {token_count}: {repr(token)}", flush=True)
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
        doc_text = r.get("document")
        # Ensure document is a string, handle boolean and None values
        if not isinstance(doc_text, str):
            doc_text = str(doc_text) if doc_text is not None else ""
        
        results.append({
            "id": r.get("id") or f"res_{i+1}",
            "score": _to_score(r.get("distance")),
            "text": doc_text or "",
            "source": meta.get("source") or "chat_session",
            "timestamp": _epoch_to_human(meta.get("timestamp")),
            "matches": query_terms,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


