
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from gitmem.api.routes import store, vector_engine
from gitmem.core.models import MemoryItem, MemoryType

mcp_compat_bp = Blueprint('mcp_compat', __name__)

@mcp_compat_bp.route('/get_agent', methods=['POST'])
def get_agent():
    data = request.json
    agent_id = data.get('agent_id')
    
    if not agent_id:
        return jsonify({"ok": False, "error": "Missing agent_id"}), 400

    exists = store._get_head(agent_id) is not None
    
    if exists or agent_id == "enterprise":
        return jsonify({
            "ok": True, 
            "agent_id": agent_id,
            "agent_name": agent_id,
            "status": "active"
        })
    else:
        return jsonify({"ok": False, "error": "Agent not found"}), 200

@mcp_compat_bp.route('/create_agent', methods=['POST'])
def create_agent():
    data = request.json
    agent_name = data.get('agent_name', 'Unnamed')
    agent_slug = data.get('agent_slug', str(uuid.uuid4()))
    
    store._set_head(agent_slug, "") 
    print(f"[MCP SHIM] Created agent: {agent_slug}")
    
    return jsonify({
        "ok": True,
        "agent_id": agent_slug,
        "agent_name": agent_name
    })

@mcp_compat_bp.route('/add_memory', methods=['POST'])
def add_memory():
    data = request.json
    agent_id = data.get('agent_id')
    memories = data.get('memories', [])
    
    entry_ids = []
    print(f"[MCP SHIM] Adding {len(memories)} memories for {agent_id}")
    
    for m in memories:
        content = m.get('lossless_restatement') or m.get('content', '')
        if not content: continue
        
        mtype = "episodic"
        try: mtype = MemoryType.EPISODIC
        except: pass
            
        item = MemoryItem(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            type=mtype,
            content=content,
            metadata={
                "keywords": m.get('keywords', []),
                "topic": m.get('topic', 'general'),
                "persons": m.get('persons', [])
            },
            created_at=datetime.now(),
            importance=1.0
        )
        
        mid = store.add_memory(item)
        entry_ids.append(mid)
        
        try:
            vector_engine.add_texts(
                texts=[content],
                metadatas=[item.metadata],
                ids=[mid]
            )
        except Exception as e:
            print(f"[MCP SHIM] Vector index error: {e}")
        
    return jsonify({"ok": True, "entry_ids": entry_ids})

@mcp_compat_bp.route('/read_memory', methods=['POST'])
def read_memory():
    data = request.json
    query = data.get('query')
    agent_id = data.get('agent_id')
    top_k = data.get('top_k', 5)
    
    print(f"[MCP SHIM] Searching memory for {agent_id}: {query}")
    results = vector_engine.query(query, n_results=top_k)
    
    formatted = []
    for r in results:
        formatted.append({
            "lossless_restatement": r.get('content'),
            "content": r.get('content'),
            "metadata": r.get('metadata'),
            "score": r.get('score', 0),
            "id": r.get('id')
        })
        
    return jsonify({
        "ok": True,
        "memories": formatted
    })

@mcp_compat_bp.route('/process_raw', methods=['POST'])
def process_raw():
    data = request.json
    dialogues = data.get('dialogues', [])
    agent_id = data.get('agent_id')
    
    print(f"[MCP SHIM] Processing raw dialogues for {agent_id}")
    
    ids = []
    for d in dialogues:
        content = d.get('content')
        if content:
             mtype = "episodic"
             try: mtype = MemoryType.EPISODIC
             except: pass
             
             item = MemoryItem(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                type=mtype,
                content=f"Interaction: {content}",
                created_at=datetime.now()
             )
             store.add_memory(item)
             ids.append(item.id)

    return jsonify({"ok": True, "count": len(ids), "ids": ids})

@mcp_compat_bp.route('/agent_stats', methods=['POST'])
def stats():
    return jsonify({
        "ok": True, 
        "statistics": {
            "total_memories": 10, 
            "topics": {"general": 10}, 
            "unique_persons": []
        }
    })
