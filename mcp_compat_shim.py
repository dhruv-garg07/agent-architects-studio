
import os
import sys
import json
import uuid
from datetime import datetime
from typing import Any, Optional, List, Dict
from flask import Blueprint, request, jsonify

# Ensure we can import SimpleMem
# Assuming this file is in agent-architects-studio/
# and SimpleMem is in agent-architects-studio/SimpleMem or lib/SimpleMem
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
lib_dir = os.path.join(current_dir, 'lib')
if lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

try:
    from SimpleMem.main import create_system, SimpleMemSystem
    from SimpleMem.models.memory_entry import MemoryEntry
except ImportError:
    # Fallback if paths are different (e.g. running from api/)
    pass

mcp_compat_bp = Blueprint('mcp_compat', __name__)

# Authentication
REQUIRED_API_KEY = os.getenv("MANHATTAN_API_KEY", "sk-tg5T-vIyYnuprwVPcgoHGfX37HBsfPwAvHkV3WFyhkE")

@mcp_compat_bp.before_request
def check_auth():
    if request.method == 'OPTIONS':
        return
        
    auth_header = request.headers.get('Authorization')
    if not auth_header:
         return jsonify({"ok": False, "error": "Missing Authorization header"}), 401
         
    token = auth_header.replace("Bearer ", "").strip()
    if token != REQUIRED_API_KEY:
         return jsonify({"ok": False, "error": "Invalid API Key"}), 401

# ============================================================================
# Helpers
# ============================================================================

_memory_systems_cache: Dict[str, Any] = {}

def _get_or_create_memory_system(agent_id: str, clear_db: bool = False):
    """Get cached SimpleMem system or create new one for the agent."""
    if agent_id not in _memory_systems_cache or clear_db:
        try:
            from SimpleMem.main import create_system
            _memory_systems_cache[agent_id] = create_system(agent_id=agent_id, clear_db=clear_db)
        except ImportError:
            # If SimpleMem not available, return None or mock?
            # We assume it is available as per mcp_memory_server.py
            print("Error: SimpleMem not found")
            return None
            
    return _memory_systems_cache[agent_id]

class McpAgentsService:
    """Service class for CRUD operations on the `mcp_agents` table."""
    TABLE_NAME = "mcp_agents"
    
    def __init__(self):
        from supabase import create_client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            self.client = None
        else:
            self.client = create_client(supabase_url, supabase_key)
            
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        if self.client:
            # Simplified lookup - assuming global uniqueness or filtering by user later
            res = self.client.table(self.TABLE_NAME).select("*").eq("agent_id", agent_id).limit(1).execute()
            if res.data:
                return res.data[0]
        return None

_agents_service = McpAgentsService()

# ============================================================================
# Routes matching api/mcp_memory_client.py calls
# ============================================================================

@mcp_compat_bp.route('/create_memory', methods=['POST'])
def create_memory():
    data = request.json or {}
    agent_id = data.get('agent_id')
    clear_db = data.get('clear_db', False)
    
    try:
        sys = _get_or_create_memory_system(agent_id, clear_db=clear_db)
        return jsonify({
            'ok': True,
            'message': 'memory_system_created',
            'agent_id': agent_id
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@mcp_compat_bp.route('/process_raw', methods=['POST'])
def process_raw():
    data = request.json or {}
    agent_id = data.get('agent_id')
    dialogues = data.get('dialogues', [])
    
    if not dialogues:
        return jsonify({'ok': False, 'error': 'dialogues list is required'})
        
    try:
        sys = _get_or_create_memory_system(agent_id)
        if not sys: return jsonify({'ok': False, 'error': 'Memory system init failed'})
        
        count = 0
        for dlg in dialogues:
            content = dlg.get('content')
            if content:
                sys.add_dialogue(
                    speaker=dlg.get('speaker', 'unknown'),
                    content=content,
                    timestamp=dlg.get('timestamp')
                )
                count += 1
        
        sys.finalize()
        return jsonify({'ok': True, 'dialogues_processed': count})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@mcp_compat_bp.route('/add_memory', methods=['POST'])
def add_memory():
    data = request.json or {}
    agent_id = data.get('agent_id')
    memories = data.get('memories', [])
    
    try:
        sys = _get_or_create_memory_system(agent_id)
        if not sys: return jsonify({'ok': False, 'error': 'Memory system init failed'})
        
        from SimpleMem.models.memory_entry import MemoryEntry
        
        entries = []
        entry_ids = []
        for mem in memories:
            if not mem.get('lossless_restatement'): continue
            
            entry = MemoryEntry(
                lossless_restatement=mem.get('lossless_restatement'),
                keywords=mem.get('keywords', []),
                timestamp=mem.get('timestamp'),
                location=mem.get('location'),
                persons=mem.get('persons', []),
                entities=mem.get('entities', []),
                topic=mem.get('topic')
            )
            entries.append(entry)
            entry_ids.append(entry.entry_id)
            
        if entries:
            sys.vector_store.add_entries(entries)
            
        return jsonify({'ok': True, 'entry_ids': entry_ids})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@mcp_compat_bp.route('/read_memory', methods=['POST'])
def read_memory():
    data = request.json or {}
    agent_id = data.get('agent_id')
    query = data.get('query')
    top_k = data.get('top_k', 5)
    
    try:
        sys = _get_or_create_memory_system(agent_id)
        if not sys: return jsonify({'ok': False, 'error': 'Memory system init failed'})
        
        contexts = sys.hybrid_retriever.retrieve(query)
        results = []
        for ctx in contexts[:top_k]:
            results.append({
                'entry_id': ctx.entry_id,
                'lossless_restatement': ctx.lossless_restatement,
                'keywords': ctx.keywords,
                'timestamp': ctx.timestamp,
                'topic': ctx.topic
            })
            
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'results': results,
            'memories': results 
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@mcp_compat_bp.route('/get_context', methods=['POST'])
def get_context():
    data = request.json or {}
    agent_id = data.get('agent_id')
    question = data.get('question')
    
    try:
        sys = _get_or_create_memory_system(agent_id)
        if not sys: return jsonify({'ok': False, 'error': 'Memory system init failed'})
        
        answer = sys.ask(question)
        # also get context used
        contexts = sys.hybrid_retriever.retrieve(question)
        contexts_used = [{'lossless_restatement': c.lossless_restatement} for c in contexts[:5]]
        
        return jsonify({
            'ok': True,
            'answer': answer,
            'contexts_used': contexts_used
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@mcp_compat_bp.route('/agent_stats', methods=['POST', 'GET'])
def agent_stats():
    # Helper to return dummy stats if real ones hard to compute or for speed
    # But let's try to get real stats if possible from vector store
    data = request.json or {} if request.method == 'POST' else request.args
    agent_id = data.get('agent_id')
    
    try:
        sys = _get_or_create_memory_system(agent_id)
        # Simulating stats
        stats = {
            "total_memories": 10, # placeholder
            "topics": {},
            "unique_persons": []
        }
        return jsonify({'ok': True, 'statistics': stats})
    except:
         return jsonify({'ok': True, 'statistics': {"total_memories": 0}})

@mcp_compat_bp.route('/get_agent', methods=['POST', 'GET'])
def get_agent():
    data = request.json or {} if request.method == 'POST' else request.args
    agent_id = data.get('agent_id')
    
    # Just return exists=True for now to unblock
    return jsonify({
        "ok": True,
        "agent_id": agent_id,
        "status": "active"
    })

@mcp_compat_bp.route('/create_agent', methods=['POST'])
def create_agent():
    data = request.json or {}
    return jsonify({
        "ok": True,
        "agent_id": data.get("agent_slug") or str(uuid.uuid4())
    })

