# api_chats.py
import os
import time
import uuid
import sys
import asyncio
import threading
import json
import re
import hashlib
from datetime import datetime
from collections import deque
from typing import List, Dict, Any, Generator, Optional
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

# Path setup
current_dir = os.path.dirname(__file__)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

sys.path[:0] = [grandparent_dir, parent_dir, current_dir]

from flask import Blueprint, request, jsonify, abort, Response
from LLM_calls.context_manager import query_llm_with_history_stream
from LLM_calls.intelligent_query_rewritten import LLMEnhancedRewriter
from LLM_calls.together_get_response import clean_response
from Octave_mem.SqlDB.sqlDbController import add_message, get_chat_history_by_session
from Octave_mem.RAG_DB_CONTROLLER.write_data_RAG import RAG_DB_Controller_CHAT_HISTORY
from Octave_mem.RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG

# Initialize controllers (singleton pattern)
_write_controller = None
_read_controller_chatH = None
_read_controller_file_data = None

def get_write_controller() -> RAG_DB_Controller_CHAT_HISTORY:
    """Get or create write controller singleton"""
    global _write_controller
    if _write_controller is None:
        _write_controller = RAG_DB_Controller_CHAT_HISTORY(
            database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY", "chroma_chat_history")
        )
    return _write_controller

def get_read_controller_chatH() -> read_data_RAG:
    """Get or create chat history read controller singleton"""
    global _read_controller_chatH
    if _read_controller_chatH is None:
        _read_controller_chatH = read_data_RAG(
            database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY", "chroma_chat_history")
        )
    return _read_controller_chatH

def get_read_controller_file_data() -> read_data_RAG:
    """Get or create file data read controller singleton"""
    global _read_controller_file_data
    if _read_controller_file_data is None:
        _read_controller_file_data = read_data_RAG(
            database=os.getenv("CHROMA_DATABASE_FILE_DATA", "chroma_file_data")
        )
    return _read_controller_file_data


# Import SimpleMem
from SimpleMem.main import SimpleMemSystem

# Initialize global components
api = Blueprint("api", __name__)
llm_enhanced_query_rewriter = LLMEnhancedRewriter()
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="api_worker")

# Reusable constants and configurations
class MessageType:
    HUMAN = "human"
    LLM = "llm"
    NOTE = "note"

# Local imports for API key validation / rate limiting & billing (no redis)
import os
from supabase import create_client
from key_utils import hash_key, parse_json_field
from local_rate_limiter import rate_limiter

# create a service-role supabase client for server-side writes
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
supabase_backend_local = None
try:
    supabase_backend_local = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
except Exception:
    supabase_backend_local = None

class ConversationMode:
    PRECISE = "precise"
    BALANCED = "balanced"
    CREATIVE = "creative"

TOP_K_CONFIG = {
    ConversationMode.PRECISE: {"chat": 40, "file": 15},
    ConversationMode.BALANCED: {"chat": 40, "file": 15},
    ConversationMode.CREATIVE: {"chat": 40, "file": 15}
}

# Optimized cache implementation with memory limits
class OptimizedChatHistoryCache:
    __slots__ = ('store', 'lock', 'max_per_session', 'max_sessions_per_user', 
                 'max_total_messages', '_total_messages')
    
    def __init__(self, max_per_session=30, max_sessions_per_user=200, max_total_messages=10000):
        self.max_per_session = max_per_session
        self.max_sessions_per_user = max_sessions_per_user
        self.max_total_messages = max_total_messages
        self._total_messages = 0
        self.store = {}  # user_id -> { session_id: tuple(message_tuples) }
        self.lock = threading.Lock()
    
    def _make_message_key(self, message: Dict) -> tuple:
        """Convert message dict to memory-efficient tuple"""
        return (
            message.get("role"),
            message.get("content", ""),
            message.get("timestamp", 0)
        )
    
    def _message_from_key(self, key: tuple) -> Dict:
        """Convert tuple back to dict"""
        return {"role": key[0], "content": key[1], "timestamp": key[2]}
    
    def get_session_history(self, user_id: str, session_id: str) -> List[Dict]:
        """Get cached history - returns list of dicts"""
        with self.lock:
            user_map = self.store.get(user_id)
            if not user_map:
                return []
            cached = user_map.get(session_id)
            return [self._message_from_key(msg) for msg in cached] if cached else []
    
    def set_session_history(self, user_id: str, session_id: str, messages: List[Dict]):
        """Set session history with memory management"""
        with self.lock:
            # Convert to tuples for memory efficiency
            message_tuples = tuple(self._make_message_key(msg) for msg in messages[-self.max_per_session:])
            
            # Update user map
            user_map = self.store.setdefault(user_id, {})
            
            # Evict oldest session if needed
            if len(user_map) >= self.max_sessions_per_user and session_id not in user_map:
                oldest_key = next(iter(user_map.keys()))
                removed = user_map.pop(oldest_key, None)
                if removed:
                    self._total_messages -= len(removed)
            
            # Update message count
            old_count = len(user_map.get(session_id, ()))
            new_count = len(message_tuples)
            self._total_messages = self._total_messages - old_count + new_count
            
            # Enforce total message limit
            if self._total_messages > self.max_total_messages:
                self._evict_oldest_messages()
            
            user_map[session_id] = message_tuples
    
    def _evict_oldest_messages(self):
        """Evict oldest messages across all sessions"""
        # Clear entire cache when limit exceeded (simplified)
        self.store.clear()
        self._total_messages = 0
    
    def append_message(self, user_id: str, session_id: str, message: Dict):
        """Append single message efficiently"""
        with self.lock:
            user_map = self.store.setdefault(user_id, {})
            cached_tuples = list(user_map.get(session_id, ()))
            
            if len(cached_tuples) >= self.max_per_session:
                cached_tuples.pop(0)
                self._total_messages -= 1
            
            cached_tuples.append(self._make_message_key(message))
            user_map[session_id] = tuple(cached_tuples)
            self._total_messages += 1
    
    def preload_user_sessions(self, user_id: str, session_ids: List[str], 
                            fetcher_fn: callable, batch_size: int = 5):
        """Preload sessions in batches for better parallelism"""
        def _preload_batch(batch: List[str]):
            for sid in batch:
                try:
                    msgs = fetcher_fn(session_id=sid, top_k=self.max_per_session)
                    self.set_session_history(user_id, sid, msgs)
                except Exception as e:
                    print(f"Preload error for {user_id}/{sid}: {e}")
        
        # Use thread pool for parallel preloading
        with ThreadPoolExecutor(max_workers=min(4, len(session_ids))) as executor:
            futures = []
            for i in range(0, len(session_ids), batch_size):
                batch = session_ids[i:i + batch_size]
                futures.append(executor.submit(_preload_batch, batch))
            
            for future in as_completed(futures):
                future.result()

# Global cache instance
chat_history_cache = OptimizedChatHistoryCache()

# SimpleMem instances cache
_simplemem_instances = {}

def get_simplemem_instance(user_id: str, session_id: str) -> SimpleMemSystem:
    """Get or create SimpleMem instance for user/session"""
    global _simplemem_instances
    instance_key = f"{session_id}"
    
    if instance_key not in _simplemem_instances:
        _simplemem_instances[instance_key] = SimpleMemSystem(
            agent_id=instance_key,
            clear_db=False
        )
    
    return _simplemem_instances[instance_key]

# Reusable utility functions with caching
@lru_cache(maxsize=1000)
def normalize_text(text: str) -> str:
    """Cached text normalization for frequently repeated texts"""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    if not text:
        return ""
    
    # Simple normalization
    text = re.sub(r"\s+", " ", text.strip())
    return text.lower()


def parse_bool(value) -> bool:
    """Parse a boolean-like value from JSON (strings, ints, bools)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    try:
        return bool(int(value))
    except Exception:
        return False

def calculate_relevance_score(query: str, document: str) -> float:
    """Optimized relevance scoring"""
    q_norm = normalize_text(query)
    d_norm = normalize_text(document)
    
    if not q_norm or not d_norm:
        return 0.0
    
    # Fast intersection calculation
    q_words = q_norm.split()
    d_words = d_norm.split()
    
    if not q_words or not d_words:
        return 0.0
    
    # Use set intersection for small texts
    if len(q_words) < 50 and len(d_words) < 50:
        q_set = set(q_words)
        d_set = set(d_words)
        intersection = q_set & d_set
        union = q_set | d_set
        
        return len(intersection) / len(union) if union else 0.0
    
    # For larger texts, count matches
    matches = 0
    for word in q_words[:20]:  # Limit to first 20 query words
        if word in d_norm:
            matches += 1
    
    return matches / max(len(q_words[:20]), 1)

def deduplicate_results(results: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """Optimized deduplication using content hashing"""
    seen = set()
    unique_results = []
    
    for result in results:
        content = result.get("document", "")
        if not content:
            continue
        
        # Simple hash for deduplication
        content_hash = hash(content[:200])
        
        if content_hash not in seen:
            seen.add(content_hash)
            unique_results.append(result)
    
    return unique_results

def split_text_into_chunks(text: str, max_sentences: int = 4, overlap: int = 1) -> List[str]:
    """Optimized text chunking"""
    if not text:
        return []
    
    # Compile regex once
    if not hasattr(split_text_into_chunks, '_sentence_pattern'):
        split_text_into_chunks._sentence_pattern = re.compile(r'(?<=[.!?]) +')
    
    sentences = split_text_into_chunks._sentence_pattern.split(text)
    chunks = []
    i = 0
    
    while i < len(sentences):
        chunk_end = min(i + max_sentences, len(sentences))
        chunk = ' '.join(sentences[i:chunk_end])
        if chunk:
            chunks.append(chunk)
        
        if chunk_end >= len(sentences):
            break
        
        i += max_sentences - overlap
    
    return chunks

# Fixed: Simple synchronous run_ai function
def run_ai(
    message: str,
    session_id: str,
    rag_context: List[Dict],
    chat_history: List[Dict],
    system_prompt: str,
    temperature: float = 0.3
) -> Generator[str, None, None]:
    
    print("Rag Context in run_ai:", rag_context,"\n\n")
    
    """
    Synchronous wrapper for LLM call.
    query_llm_with_history_stream returns a generator, not a coroutine.
    """
    try:
        # Direct call - this returns a generator
        return query_llm_with_history_stream(
            message=message,
            rag_context=rag_context,
            chat_history=chat_history,
            system_prompt=system_prompt,
            temperature=temperature
        )
    except Exception as e:
        # Return a generator that yields the error
        def error_generator():
            yield f"Error in LLM call: {str(e)}"
        return error_generator()

# API endpoints
@api.get("/web/get_sessions")
def list_sessions():
    """List user sessions with background preloading"""
    user_id = request.args.get("id")
    if not user_id:
        abort(400, "Missing user ID")
    
    try:
        # Use existing async pattern from original code
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        session_ids = loop.run_until_complete(
            get_read_controller_chatH().list_session_ids(id=user_id)
        )
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        session_ids = []
    finally:
        if 'loop' in locals():
            loop.close()
    
    # Preload sessions in background
    if session_ids:
        ids = []
        for s in session_ids:
            if isinstance(s, str):
                ids.append(s)
            elif isinstance(s, dict):
                ids.append(s.get('id') or s.get('thread_id'))
        
        ids = [i for i in ids if i]
        
        def _fetcher(session_id, top_k=30):
            return get_chat_history_by_session(
                user_id=user_id, session_id=session_id, top_k=top_k
            )
        
        # Non-blocking preload
        threading.Thread(
            target=chat_history_cache.preload_user_sessions,
            args=(user_id, ids[:10], _fetcher),
            daemon=True
        ).start()
    
    return jsonify(session_ids)


@api.post("/web/create_session")
def create_session():
    """Create new chat session"""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    
    if not user_id:
        abort(400, "Missing user_id")
    
    thread_id = str(uuid.uuid4())
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        thread_id_created = thread_id_created = loop.run_until_complete(
            get_read_controller_chatH().create_session(
                id=user_id, thread_id=thread_id, created=created
            )
        )
    except Exception as e:
        print(f"Error creating session: {e}")
        thread_id_created = thread_id
    finally:
        if 'loop' in locals():
            loop.close()
    
    return jsonify({"thread_id": thread_id_created, "createdAt": created})

@api.get("/web/sessions/<thread_id>/messages")
def get_messages(thread_id: str):
    """Get messages for a session with cache-first strategy"""
    user_id = request.args.get("id")
    
    if not user_id:
        abort(400, "Missing user ID")
    
    # Try cache first
    cached = chat_history_cache.get_session_history(user_id, thread_id)
    if cached:
        return jsonify({"messages": cached})
    
    # Fallback to database
    messages = get_chat_history_by_session(
        user_id=user_id, session_id=thread_id, top_k=100
    )
    
    # Update cache
    chat_history_cache.set_session_history(user_id, thread_id, messages)
    
    return jsonify({"messages": messages})

@api.post("/web/chat")
def chat_and_store():
    """Main chat endpoint using SimpleMem"""
    # Start timing
    start_time = time.time()
    
    # Parse request
    data = request.get_json(force=True)
    thread_id = data.get("thread_id")
    user_id = data.get("user_id")
    user_msg = data.get("message", "").strip()
    use_file_rag = data.get("use_file_rag", False)
    conversation_mode = data.get("mode", ConversationMode.BALANCED)
    # Optional boolean: whether to use LLM-based query rewriting; default False
    rewrite_llm = parse_bool(data.get("rewrite_llm", False))
    
    if not thread_id or not user_id or not user_msg:
        abort(400, "Missing required fields")

    # --- API Key validation and rate limiting (if provided) ---
    auth_header = request.headers.get('Authorization') or request.headers.get('authorization')
    api_key_plain = None
    if auth_header and auth_header.lower().startswith('bearer '):
        api_key_plain = auth_header.split(None, 1)[1].strip()
    elif request.headers.get('X-API-Key'):
        api_key_plain = request.headers.get('X-API-Key')

    key_record = None
    key_limits = None
    estimated_tokens = data.get('estimated_tokens') or max(1, len(user_msg.split()) // 3)

    if api_key_plain:
        try:
            hashed = hash_key(api_key_plain)
            if supabase_backend_local is None:
                abort(500, 'Server misconfiguration: supabase client unavailable')

            # Prefer the new 'hashed_key' column when present
            resp = supabase_backend_local.table('api_keys').select('*').eq('hashed_key', hashed).eq('status', 'active').limit(1).execute()
            data_rows = getattr(resp, 'data', None) or (resp.data if hasattr(resp, 'data') else None) or resp
            if not data_rows:
                # Fallback: some installations used a legacy 'key' column to store values; look there for the hash
                resp2 = supabase_backend_local.table('api_keys').select('*').eq('key', hashed).eq('status', 'active').limit(1).execute()
                data_rows = getattr(resp2, 'data', None) or (resp2.data if hasattr(resp2, 'data') else None) or resp2
                if not data_rows:
                    abort(401, 'Invalid API key')

            key_record = data_rows[0]

            perms = parse_json_field(key_record.get('permissions'))
            if not perms.get('chat', True):
                abort(403, 'API key does not have chat permission')

            key_limits = parse_json_field(key_record.get('limits'))

            # Try to reserve capacity
            allowed = rate_limiter.allow_request(key_record.get('id'), key_limits, estimated_tokens)
            if not allowed:
                return jsonify({'error': 'rate_limited', 'message': 'Rate limit exceeded'}), 429

        except Exception as e:
            print('[API KEY] validation error:', e)
            abort(401, 'Invalid API key')

    else:
        # Not using API key; proceed without rate limiting here (web UI flows still apply)
        key_record = None
    
    # Get SimpleMem instance
    simplemem = get_simplemem_instance(user_id, thread_id)
    
    # Get chat history
    print(f"[CHAT] Phase 4: Chat history retrieval")
    history_start = time.time()
    
    chat_history = chat_history_cache.get_session_history(user_id, thread_id)
    if not chat_history:
        query_length = len(user_msg.split())
        history_top_k = min(30, max(18, query_length * 2))
        
        chat_history = get_chat_history_by_session(
            user_id=user_id,
            session_id=thread_id,
            top_k=history_top_k
        )
        
        chat_history_cache.set_session_history(user_id, thread_id, chat_history)
    
    print(f"[CHAT] Retrieved {len(chat_history)} history messages in {time.time() - history_start:.2f}s")
    
    # System prompt
    system_prompt =  """You are a helpful AI assistant that provides well-formatted responses.
Always format your responses using proper markdown-style formatting:

1. Use **bold** for emphasis and important terms
2. Use *italic* for subtle emphasis
3. Use # for headers, ## for subheaders
4. Use - or * for bullet points
5. Use `inline code` for code snippets
6. Use ```language for code blocks:

```python
def example():
    print("This is a code block")
Keep responses clear and well-structured

Use proper spacing between sections

Break down complex information into digestible chunks

Respond helpfully and format your answers for maximum readability."""
    
    # Prepare final query
    final_query = user_msg
    
    print(f"[CHAT] Total pre-LLM processing time: {time.time() - start_time:.2f}s")
    
    # Background storage function
        
    # ---------- Lane 1: DB (ordered) ----------
    def store_db_ordered(full_text: str):
        add_message(user_id, MessageType.HUMAN, user_msg, session_id=thread_id)
        add_message(user_id, MessageType.LLM, full_text, session_id=thread_id)


    # ---------- Lane 2: Cache (ordered) ----------
    def store_cache_ordered(full_text: str):
        ts = int(time.time())

        chat_history_cache.append_message(user_id, thread_id, {
            "role": "user",
            "content": user_msg,
            "timestamp": ts
        })

        chat_history_cache.append_message(user_id, thread_id, {
            "role": "assistant",
            "content": full_text,
            "timestamp": ts
        })


    # ---------- Lane 3: SimpleMem (ordered) ----------
    def store_simplemem_ordered(full_text: str):
        now = datetime.now().isoformat()

        simplemem.add_dialogue(
            speaker="user",
            content=user_msg,
            timestamp=now
        )

        simplemem.add_dialogue(
            speaker="assistant",
            content=full_text,
            timestamp=now
        )

        simplemem.finalize()


    # ---------- Background entry point ----------
    def store_messages_background(full_text: str):
        try:
            _executor.submit(store_db_ordered, full_text)
            _executor.submit(store_cache_ordered, full_text)
            _executor.submit(store_simplemem_ordered, full_text)
        except Exception as e:
            print(f"[BACKGROUND] Storage error: {e}")
    
    # Streaming response generator
    def clean_token(token: str, is_first: bool = False) -> str:
        """
        Clean token for streaming - remove markers and leading space only on first token.
        
        Args:
            token: Raw token from LLM
            is_first: Whether this is the first token (strip leading whitespace)
            
        Returns:
            Cleaned token preserving word separation spaces
        """
        if not token:
            return ""
        
        # Remove end markers
        token = token.replace("<|end|>", "")
        token = token.replace("[END FINAL RESPONSE]", "")
        
        # Remove markdown table pipes
        token = token.replace("|", "")
        
        # ONLY strip leading whitespace from first token
        if is_first:
            token = token.lstrip()
        
        return token

    def generate_streaming_response():
        """Generator for streaming SSE response with loader status"""
        full_reply_text = ""
        token_count = 0
        first_token_sent = False
        
        try:
            # Send initial loading state
            yield f"data: {json.dumps({'type': 'loading', 'status': 'initializing', 'message': 'Preparing context and retrieving information...'})}\n\n"
            time.sleep(0.1)  # Small delay to ensure client receives loading state
            
            print(f"[STREAM] Starting LLM generation for query: {final_query}...")
            
            # Get answer from SimpleMem using ask() method
            llm_start = time.time()
            
            # Get answer and context from SimpleMem
            simplemem_answer = simplemem.ask(final_query)

            # Convert SimpleMem answer to rag_context format for LLM
            rag_context = [{
                "id": "simplemem_context",
                "document": simplemem_answer,
                "score": 1.0,
                "source": "simplemem",
                "metadata": {}
            }]

            print(f"[CHAT] SimpleMem context retrieved: {simplemem_answer[:200]}...")
            
            # Call run_ai with SimpleMem context instead of direct answer
            reply_generator = run_ai(
                message=final_query,
                session_id=thread_id,
                rag_context=rag_context,  # Use SimpleMem answer as context
                chat_history=chat_history,
                system_prompt=system_prompt,
                temperature=0.7 if conversation_mode == ConversationMode.CREATIVE else 0.3
            )
                        
            # For streaming, we'll simulate token generation from the answer
            # In production, you might want to modify SimpleMem to support streaming
            # tokens = answer.split()
            # print(f"[STREAM] SimpleMem generated {len(tokens)} tokens")
            
            # Send status: streaming started
            yield f"data: {json.dumps({'type': 'loading', 'status': 'streaming', 'message': 'Generating response...'})}\n\n"
            
            # Stream tokens (simulated from complete answer)
            for token in reply_generator:
                token_count += 1
                full_reply_text += token + ""
                
                # Clean the token
                cleaned_token = clean_token(token, is_first=(not first_token_sent))
                
                if not first_token_sent:
                    if not cleaned_token or not cleaned_token.strip():
                        continue
                    first_token_sent = True
                    yield f"data: {json.dumps({'type': 'token', 'content': cleaned_token + ''})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'token', 'content': token + ''})}\n\n"
                
                # Small delay for streaming effect
                time.sleep(0.01)
            
            llm_time = time.time() - llm_start
            print(f"[STREAM] SimpleMem generation completed in {llm_time:.2f}s, {token_count} tokens")
            
            # Send status: processing response
            yield f"data: {json.dumps({'type': 'loading', 'status': 'processing', 'message': 'Processing and finalizing response...', 'tokens': token_count})}\n\n"
            
            # Clean response
            cleaned_response = clean_response(full_reply_text.strip())
            
            # Remove any remaining markers
            for marker in ["<|end|>", "[END FINAL RESPONSE]"]:
                cleaned_response = cleaned_response.replace(marker, "")
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done', 'full_response': cleaned_response.strip(), 'tokens_generated': token_count, 'processing_time': llm_time})}\n\n"
            
            print(f"[STREAM] Streaming completed, total time: {time.time() - start_time:.2f}s")
            
            # Start background storage
            threading.Thread(
                target=store_messages_background,
                args=(cleaned_response,),
                daemon=True
            ).start()
            
        except Exception as e:
            error_msg = f"Error in streaming response: {str(e)}"
            print(f"[STREAM] {error_msg}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        finally:
            # Record usage and release concurrency if an API key was used
            try:
                if key_record and 'id' in key_record:
                    # Update usage table with token counts
                    if supabase_backend_local:
                        try:
                            usage = {
                                'key_id': key_record.get('id'),
                                'tokens_used': int(token_count),
                                'model': data.get('model') or 'unknown',
                                'prompt_tokens': int(estimated_tokens),
                                'completion_tokens': int(token_count),
                                'cost': None,
                                'timestamp': datetime.utcnow().isoformat()
                            }
                            supabase_backend_local.table('api_usage').insert(usage).execute()
                            # update last_used_at
                            supabase_backend_local.table('api_keys').update({'last_used_at': datetime.utcnow().isoformat()}).eq('id', key_record.get('id')).execute()
                        except Exception as e:
                            print('[BILLING] failed to record usage:', e)

                    # release concurrency
                    try:
                        rate_limiter.end_request(key_record.get('id'))
                    except Exception as e:
                        print('[RATE] error releasing concurrency:', e)
            except Exception as e:
                print('[STREAM-FINAL] unexpected error in finally block:', e)
    
    return Response(generate_streaming_response(), mimetype='text/event-stream')

@api.post("/web/notes")
def store_note():
    """Store a note using SimpleMem"""
    data = request.get_json(force=True) or {}
    user_id = data.get("user_id", "user123")
    thread_id = data.get("thread_id", "")
    note_text = data.get("text", "")
    
    if not user_id or not thread_id or not note_text:
        abort(400, "Missing required fields")
    
    # Get SimpleMem instance
    simplemem = get_simplemem_instance(user_id, thread_id)
    
    # Store note as dialogue
    simplemem.add_dialogue(
        speaker="note",
        content=note_text,
        timestamp=datetime.now().isoformat()
    )
    
    # Finalize
    simplemem.finalize()
    
    return jsonify({"status": "success", "message": "Note stored"})

# Will be implemented by Hybrid Search feature from Simplemem stack in future.
@api.post("/web/rag")
def rag_search():
    """RAG search endpoint"""
    data = request.get_json(force=True) or {}
    user_id = data.get("user_id")
    query = (data.get("query") or "").strip()
    thread_id = data.get("thread_id")
    top_k = int(data.get("top_k", 5))
    
    if not user_id or not query:
        abort(400, "Missing user_id or query")
    
    # Because every session has to independent, the main focus now is thread id as its the collection name to search from.
    rows = get_read_controller_chatH().fetch_related_to_query(
        user_ID=thread_id,
        query=query,
        top_k=top_k
    )
    
    # Allow all to come, no metadata filter as now its different collection.
    # if thread_id:
    #     rows = [
    #         r for r in rows
    #         if (r.get("metadata") or {}).get("conversation_thread") == thread_id
    #     ]
    
    # Convert to UI format
    q_terms = [t.lower() for t in query.split() if len(t) > 2]
    results = normalize_rag_rows(rows, q_terms)
    
    return jsonify({"results": results})

@api.post("/web/rag/feedback")
def rag_feedback():
    """Handle RAG feedback"""
    data = request.get_json(force=True) or {}
    # Implement feedback storage here
    return jsonify({"ok": True})

# Helper functions for RAG result normalization
def epoch_to_human(ts):
    """Convert epoch to human readable format"""
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(float(ts)))
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

def distance_to_score(distance):
    """Convert distance to score"""
    try:
        return 1.0 / (1.0 + float(distance))
    except Exception:
        return 0.0

def normalize_rag_rows(rows, query_terms):
    """Normalize RAG rows for UI display"""
    results = []
    
    for i, row in enumerate(rows or []):
        meta = row.get("metadata", {})
        doc_text = row.get("document", "")
        
        if not isinstance(doc_text, str):
            doc_text = str(doc_text) if doc_text is not None else ""
        
        results.append({
            "id": row.get("id") or f"res_{i+1}",
            "score": distance_to_score(row.get("distance")),
            "text": doc_text[:500],
            "source": meta.get("source") or "chat_session",
            "timestamp": epoch_to_human(meta.get("timestamp")),
            "matches": query_terms[:5]
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# Cleanup
def cleanup():
    """Cleanup resources"""
    _executor.shutdown(wait=False)
    
    if hasattr(split_text_into_chunks, '_sentence_pattern'):
        delattr(split_text_into_chunks, '_sentence_pattern')

import atexit
atexit.register(cleanup)