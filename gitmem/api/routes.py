from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_file, current_app, flash
from flask_login import login_required, current_user
from ..core.agent_manager import AgentManager
from ..core.memory_store import MemoryStore
from ..core.vector_engine import VectorEngine
from ..core.models import MemoryItem
import json
import io
import os
from datetime import datetime

gitmem_bp = Blueprint('gitmem', __name__, url_prefix='/gitmem', template_folder='../../templates/gitmem')

# Initialize singletons
# Note: These should ideally be initialized in the app factory or passed in, 
# but for this structure we initialize them here as requested by websocket_events.py
store = MemoryStore()
vector_engine = VectorEngine()
store.vector_engine = vector_engine
agent_manager = AgentManager(store)

def get_sources_status():
    # Check connections
    supabase_on = False
    try:
        if hasattr(store, 'db') and store.db and store.db.client and not getattr(store.db, '_disabled', False):
            supabase_on = True
    except: pass

    # Get Chroma stats safely
    chroma_stats = {}
    chroma_on = False
    chroma_count = 0
    try:
        chroma_stats = vector_engine.get_stats()
        chroma_count = chroma_stats.get('embeddings', 0)
        chroma_on = str(chroma_stats.get('freshness')) == 'Connected'
    except: pass

    return {
        'supabase': supabase_on,
        'chromadb': chroma_on,
        'chromadb_count': chroma_count,
        'mcp': True, 
        'local_count': store.count_memories() 
    }

@gitmem_bp.route('/')
@login_required
def landing():
    # 1. Fetch User's Agents from 'agent_profiles' (Supabase)
    # This ensures we only show agents owned by the logged-in user.
    my_agents = []
    try:
        if hasattr(store, 'db') and store.db and store.db.client:
             # Using the underlying supabase client from the store connector
             res = store.db.client.table('api_agents').select('*').eq('user_id', current_user.id).execute()
             my_agents = res.data or []
    except Exception as e:
        print(f"Error fetching user agents: {e}")
        # Fallback? If DB fails, we might show nothing or local?
        # For "Only for that logged in user", better to show nothing/error than leak data.
        pass

    agents_map = {}
    
    # 2. Build base map from Owned Agents
    for agent in my_agents:
        aid = agent.get('agent_id')
        if not aid: continue
        
        agents_map[aid] = {
            'id': aid,
            'name': agent.get('agent_slug') or agent.get('agent_name') or f"Agent {aid[:4]}",
            'description': agent.get('description', 'Owned Agent'),
            'status': 'offline',
            'last_active': None,
            'memory_count': store.count_memories(aid),
            'commit_count': 0, 
            'source': 'Supabase'
        }

    # 2.5. Include Local/Known Agents (FileSystem)
    try:
        local_ids = store.list_known_agents()
        for lid in local_ids:
            if lid not in agents_map:
                agents_map[lid] = {
                    'id': lid,
                    'name': f"Agent {lid[:4]}",
                    'description': 'Cloud Repository',
                    'status': 'offline',
                    'last_active': None,
                    'memory_count': store.count_memories(lid),
                    'commit_count': 0,
                    'source': 'Cloud'
                }
    except Exception as e:
        print(f"Error listing local agents: {e}")

    # 3. Check Active Agents (In-memory overlay)
    active_list = agent_manager.get_active_agents()
    for a in active_list:
        aid = a.get('agent_id')
        if not aid: continue
        
        # If active but not in map, add it
        if aid not in agents_map:
             agents_map[aid] = {
                'id': aid,
                'name': a.get('name', f"Agent {aid[:4]}"),
                'description': f"Active Model: {a.get('model', 'Unknown')}",
                'status': 'online',
                'last_active': a.get('last_active'),
                'memory_count': store.count_memories(aid),
                'commit_count': 0,
                'source': 'MCP' # Or In-Memory
            }
        else:
            # Update status if this owned agent is online
            agents_map[aid]['status'] = 'online'
            agents_map[aid]['last_active'] = a.get('last_active')
            if 'Active model' not in agents_map[aid]['description']:
                 agents_map[aid]['description'] += f" • Active: {a.get('model')}"

    # 4. Get Commit Counts (Optimized: only for my agents)
    all_commits = store.get_commits()
    commit_counts = {}
    for c in all_commits:
        if c.agent_id:
            commit_counts[c.agent_id] = commit_counts.get(c.agent_id, 0) + 1
            
    for aid, data in agents_map.items():
        data['commit_count'] = commit_counts.get(aid, 0)

    agents = list(agents_map.values())
    
    # Sort agents: Online first, then by Name
    agents.sort(key=lambda x: (x['status'] != 'online', x['name']))

    # 5. Stats
    stats = {
        'active_agents': len([a for a in agents if a['status'] == 'online']), 
        'total_repositories': len(agents), 
        'total_memories': sum(a['memory_count'] for a in agents),
        'total_commits': sum(a['commit_count'] for a in agents)
    }

    # 6. Sources
    sources = get_sources_status()

    return render_template('landing.html', agents=agents, stats=stats, sources=sources)

@gitmem_bp.route('/agent/<agent_id>/fs')
@gitmem_bp.route('/agent/<agent_id>/fs/<path:virtual_path>')
@login_required
def agent_fs_view(agent_id, virtual_path=""):
    """
    Virtual Filesystem View: Browse directories.
    """
    try:
        items = store.fs.list_dir(agent_id, virtual_path)
        agent = agent_manager.get_profile(agent_id)
        if not agent:
            # Re-fetch from DB if manager doesn't have it
            agent_name = f"Agent {agent_id}"
            try:
                res = store.db.client.table('api_agents').select('agent_name, agent_slug').eq('agent_id', agent_id).execute()
                if res.data:
                    agent_name = res.data[0].get('agent_slug') or res.data[0].get('agent_name', agent_name)
            except: pass
            agent = type("Mock", (), {"id": agent_id, "name": agent_name, "status": "offline"})

        # Fetch stats for header
        memory_count = store.count_memories(agent_id)
        all_commits = store.get_commits()
        commit_count = len([c for c in all_commits if c.agent_id == agent_id])

        return render_template('gitmem/file_browser.html', 
                             agent=agent, 
                             items=items, 
                             current_path=virtual_path,
                             memory_count=memory_count,
                             commit_count=commit_count,
                             sources=get_sources_status())
    except Exception as e:
        flash(f"Error accessing filesystem: {str(e)}", "error")
        return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/view/<path:virtual_path>')
@login_required
def agent_file_view(agent_id, virtual_path):
    """
    Virtual Filesystem View: View file content.
    """
    try:
        file_data = store.fs.read_file(agent_id, virtual_path)
        if not file_data:
            flash("File not found", "error")
            return redirect(url_for('gitmem.agent_fs_view', agent_id=agent_id))
            
        agent = agent_manager.get_profile(agent_id)
        if not agent:
            # Re-fetch from DB if manager doesn't have it
            agent_name = f"Agent {agent_id}"
            agent_slug = None
            try:
                res = store.db.client.table('api_agents').select('agent_name, agent_slug').eq('agent_id', agent_id).execute()
                if res.data:
                    agent_slug = res.data[0].get('agent_slug')
                    agent_name = agent_slug or res.data[0].get('agent_name', agent_name)
            except: pass
            agent = type("Mock", (), {"id": agent_id, "name": agent_name, "slug": agent_slug, "status": "offline"})

        # Fetch stats for header
        memory_count = store.count_memories(agent_id)
        all_commits = store.get_commits()
        commit_count = len([c for c in all_commits if c.agent_id == agent_id])

        return render_template('gitmem/file_view.html', 
                             agent=agent, 
                             path=virtual_path, 
                             content=file_data['content'],
                             metadata=file_data.get('metadata', {}),
                             memory_count=memory_count,
                             commit_count=commit_count,
                             sources=get_sources_status())
    except Exception as e:
        flash(f"Error reading file: {str(e)}", "error")
        # Try to go up one level
        parent = "/".join(virtual_path.split("/")[:-1])
        return redirect(url_for('gitmem.agent_fs_view', agent_id=agent_id, virtual_path=parent))

@gitmem_bp.route('/agent/<agent_id>')
@login_required
def agent_dashboard(agent_id):
    # Verify ownership?
    try:
        if hasattr(store, 'db') and store.db and store.db.client:
             res = store.db.client.table('api_agents').select('agent_id').eq('agent_id', agent_id).eq('user_id', current_user.id).execute()
             if not res.data:
                 flash("Agent not found or access denied.", "error")
                 return redirect(url_for('gitmem.landing'))
    except:
        pass

    agent = agent_manager.get_profile(agent_id)
    if not agent:
        agent_name = f"Agent {agent_id}"
        agent_desc = "Offline Agent"
        try:
             res = store.db.client.table('api_agents').select('agent_name, agent_slug, description').eq('agent_id', agent_id).execute()
             if res.data:
                 agent_name = res.data[0].get('agent_slug') or res.data[0].get('agent_name', agent_name)
                 agent_desc = res.data[0].get('description', agent_desc)
        except: pass

        agent = type("Mock", (), {
            "id": agent_id, "name": agent_name, "description": agent_desc, 
            "status": "offline", "memory_count": 0, "commit_count": 0, "source": "Cloud"
        })

    # Get stats
    folder_stats = store.get_folder_structure_stats(agent_id)
    
    # Get minimal lists for UI previews
    context = []
    for mtype in ["episodic", "semantic", "procedural"]:
        mems = store.list_memories(agent_id, mtype, limit=2)
        context.extend(mems)
    context.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    
    # Commits
    all_commits = store.get_commits() 
    agent_commits = [c for c in all_commits if c.agent_id == agent_id]
    commit_count = len(agent_commits)
    latest_commit = agent_commits[0] if agent_commits else None
    
    # Activity
    recent_activity = store.get_activity_feed(limit=50) 
    agent_activity = [a for a in recent_activity if a.get('agent_id') == agent_id]
    
    # Branches
    branches = list(store.list_branches().keys())
    
    return render_template('agent_dashboard.html', 
                         agent=agent, 
                         memory_count=folder_stats['total_memories'],
                         commit_count=commit_count,
                         latest_commit=latest_commit,
                         context_sources=[], 
                         folder_structure=folder_stats['structure'],
                         recent_context=context[:5],
                         activity_feed=agent_activity[:5],
                         branches=branches,
                         index_stats=vector_engine.get_stats(),
                         sources=get_sources_status())

@gitmem_bp.route('/agent/<agent_id>/commits')
@login_required
def agent_commits(agent_id):
    agent = agent_manager.get_profile(agent_id) or type("Mock", (), {"id": agent_id, "name": agent_id})
    all_commits = store.get_commits()
    commits = [c for c in all_commits if c.agent_id == agent_id]
    return render_template('commit_log.html', agent=agent, commits=commits)

@gitmem_bp.route('/agent/<agent_id>/pulls')
@login_required
def pulls(agent_id):
    flash("Pull requests not yet implemented.", "info")
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/issues')
@login_required
def issues(agent_id):
    flash("Issues not yet implemented.", "info")
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/settings')
@login_required
def settings(agent_id):
    flash("Settings not yet implemented.", "info")
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/actions')
@login_required
def actions(agent_id):
    flash("Actions not yet implemented.", "info")
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/projects')
@login_required
def projects(agent_id):
    flash("Projects not yet implemented.", "info")
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/insights')
@login_required
def insights(agent_id):
    flash("Insights not yet implemented.", "info")
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/agent/<agent_id>/context/<category>')
@login_required
def agent_context_category(agent_id, category):
    return redirect(url_for('gitmem.agent_fs_view', agent_id=agent_id, virtual_path=f'context/{category}'))

@gitmem_bp.route('/agent/<agent_id>/docs/<folder>')
@login_required
def agent_documents(agent_id, folder):
    return redirect(url_for('gitmem.agent_fs_view', agent_id=agent_id, virtual_path=f'docs/{folder}'))

@gitmem_bp.route('/agent/<agent_id>/checkpoints/<type>')
@login_required
def agent_checkpoints(agent_id, type):
    return redirect(url_for('gitmem.agent_fs_view', agent_id=agent_id, virtual_path=f'checkpoints/{type}'))

@gitmem_bp.route('/agent/<agent_id>/logs/<type>')
@login_required
def agent_logs(agent_id, type):
    return redirect(url_for('gitmem.agent_fs_view', agent_id=agent_id, virtual_path=f'logs/{type}'))

@gitmem_bp.route('/agent/<agent_id>/export')
@login_required
def export_data(agent_id):
    """
    Export all agent data (profile, memories, commits) as a JSON file.
    """
    # Verify ownership
    if hasattr(store, 'db') and store.db and store.db.client:
        try:
             res = store.db.client.table('api_agents').select('agent_id').eq('agent_id', agent_id).eq('user_id', current_user.id).execute()
             if not res.data:
                 flash("Agent not found or access denied.", "error")
                 return redirect(url_for('gitmem.landing'))
        except: pass

    # Fetch data
    agent_profile = agent_manager.get_profile(agent_id)
    # If using Mock object from manager, convert directly
    profile_data = {
        "id": agent_id,
        "name": getattr(agent_profile, "name", agent_id),
        "description": getattr(agent_profile, "description", ""),
        "status": getattr(agent_profile, "status", "offline")
    }

    # Fetch memories
    memories = []
    for mtype in ["episodic", "semantic", "procedural"]:
        mems = store.list_memories(agent_id, mtype, limit=1000)
        for m in mems:
            memories.append({
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "importance": m.importance,
                "created_at": m.created_at.isoformat() if m.created_at else None
            })

    # Fetch commits
    all_commits = store.get_commits()
    commits = [
        {
            "hash": c.hash,
            "message": c.message,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None
        }
        for c in all_commits if c.agent_id == agent_id
    ]

    export_payload = {
        "agent": profile_data,
        "memories": memories,
        "commits": commits,
        "exported_at": datetime.utcnow().isoformat()
    }

    # Return as file download
    return send_file(
        io.BytesIO(json.dumps(export_payload, indent=2).encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=f"gitmem-{agent_id}-export.json"
    )


@gitmem_bp.route('/create')
@login_required
def create_agent_form():
    return render_template('create_agent.html')

@gitmem_bp.route('/api/create', methods=['POST'])
@login_required
def api_create_agent():
    agent_id = request.form.get('agent_id')
    name = request.form.get('name')
    description = request.form.get('description')
    initial_memory = request.form.get('initial_memory')
    
    if not agent_id:
        return jsonify({'error': 'Agent ID is required'}), 400
        
    # Create valid agent ID
    agent_id = agent_id.lower().replace(' ', '-')
    
    # 0. Register Agent in `agent_profiles` with Owner
    try:
        if hasattr(store, 'db') and store.db and store.db.client:
            agent_data = {
                'agent_id': agent_id,
                'agent_name': name or f"Agent {agent_id}",
                'agent_slug': agent_id,
                'description': description or "Created via GitMem",
                'user_id': current_user.id,
                'permissions': {},
                'limits': {},
                'metadata': {
                    'status': 'active',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
            }
            # Upsert to avoid dupes? Or allow fail? 
            # Insert is better to catch conflict.
            store.db.client.table('api_agents').upsert(agent_data).execute()
    except Exception as e:
        print(f"Error creating agent profile: {e}")
        # Continue? If DB fails, local creation might still work, but ownership will be lost.
        # Ideally return error.
        return jsonify({'error': f'Failed to register agent: {str(e)}'}), 500

    # 1. Initialize empty commit / folder structure via add_memory (auto-creates)
    # We don't have an explicit "create repo" method in MemoryStore yet, 
    # but adding a memory will initialize folders.
    
    # Send initial heartbeat to register as "online" temporarily
    agent_manager.register_heartbeat(agent_id, model="User Created")
    
    # 2. Add initial memory if present
    if initial_memory:
        mem = MemoryItem(
            id=os.urandom(8).hex(),
            agent_id=agent_id,
            type="semantic",
            content=initial_memory,
            importance=1.0,
            created_at=datetime.now()
        )
        store.add_memory(mem)
        vector_engine.add_memory(mem)
        
    return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

@gitmem_bp.route('/api/memory', methods=['POST'])
def add_memory():
    data = request.json
    agent_id = data.get('agent_id')
    content = data.get('content')
    mtype = data.get('type', 'episodic')
    importance = data.get('importance', 0.5)
    
    if not agent_id or not content:
        return jsonify({'error': 'Missing required fields'}), 400
        
    # Create memory item
    mem = MemoryItem(
        id=os.urandom(8).hex(),
        agent_id=agent_id,
        type=mtype,
        content=content,
        importance=importance,
        created_at=datetime.now()
    )
    
    # Save
    store.add_memory(mem)
    
    # Add to vector index
    vector_engine.add_memory(mem)
    
    return jsonify({'status': 'success', 'id': mem.id})

@gitmem_bp.route('/api/agent/<agent_id>/fs')
@gitmem_bp.route('/api/agent/<agent_id>/fs/<path:virtual_path>')
@login_required
def agent_fs_list(agent_id, virtual_path=""):
    """
    Virtual Filesystem API: List directory contents.
    """
    try:
        items = store.fs.list_dir(agent_id, virtual_path)
        return jsonify({
            'status': 'success',
            'agent_id': agent_id,
            'path': virtual_path,
            'items': items
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@gitmem_bp.route('/api/agent/<agent_id>/file/<path:virtual_path>')
@login_required
def agent_fs_file(agent_id, virtual_path):
    """
    Virtual Filesystem API: Read file content.
    """
    try:
        file_data = store.fs.read_file(agent_id, virtual_path)
        if not file_data:
            return jsonify({'status': 'error', 'message': 'File not found'}), 404
            
        return jsonify({
            'status': 'success',
            'agent_id': agent_id,
            'path': virtual_path,
            **file_data
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@gitmem_bp.route('/api/agent/<agent_id>/sync', methods=['POST'])
@login_required
def api_agent_sync(agent_id):
    """Placeholder for agent-specific sync."""
    return jsonify({
        'status': 'success',
        'message': f'Agent {agent_id} synced successfully.'
    })

@gitmem_bp.route('/api/sync-sources', methods=['POST'])
@login_required
def sync_sources():
    """
    Force a check of all data sources and ensure consistency.
    """
    synced_count = 0
    claimed_count = 0
    errors = []
    
    try:
        # 1. Fetch Owned Agents
        my_agents = set()
        if hasattr(store, 'db') and store.db and getattr(store.db, 'client', None):
             try:
                 print("[Sync] Step 1: Fetching owned agents...", flush=True)
                 res = store.db.client.table('api_agents').select('agent_id').eq('user_id', current_user.id).execute()
                 if res.data:
                     for row in res.data:
                         my_agents.add(row['agent_id'])

                 # 2. Discovery & Claiming
                 print("[Sync] Step 2: Scanning recent memories...", flush=True)
                 # Limit 50 is safe
                 mem_res = store.db.client.table('gitmem_memories').select('agent_id').order('created_at', desc=True).limit(50).execute()
                 
                 memory_agents = set()
                 if mem_res.data:
                     for row in mem_res.data:
                         if row.get('agent_id'):
                             memory_agents.add(row['agent_id'])
                 
                 if memory_agents:
                     candidates = memory_agents - my_agents 
                     print(f"[Sync] Candidates to check: {len(candidates)}", flush=True)
                     
                     if candidates:
                         existing_res = store.db.client.table('api_agents').select('agent_id').in_('agent_id', list(candidates)).execute()
                         existing_ids = set(r['agent_id'] for r in existing_res.data) if existing_res.data else set()
                         
                         orphans = candidates - existing_ids
                         
                         if orphans:
                             print(f"[Sync] Claiming orphans: {orphans}", flush=True)
                             new_profiles = []
                             now_iso = datetime.utcnow().isoformat()
                             for oid in orphans:
                                 new_profiles.append({
                                     'agent_id': oid,
                                     'agent_name': f"Agent {oid}", 
                                     'agent_slug': oid,
                                     'description': 'Discovered from Memory History',
                                     'user_id': current_user.id,
                                     'permissions': {},
                                     'limits': {},
                                     'metadata': {
                                        'status': 'offline',
                                        'created_at': now_iso,
                                        'updated_at': now_iso
                                     }
                                 })
                             
                             store.db.client.table('api_agents').insert(new_profiles).execute()
                             claimed_count = len(new_profiles)
                             my_agents.update(orphans)

             except Exception as e:
                 print(f"[Sync] DB Error: {e}", flush=True)
                 errors.append(str(e))
                 
        # 3. sync_sources local sync removed.
        
        print(f"[Sync] Done. Synced {len(my_agents)}, Claimed {claimed_count}", flush=True)        
        return jsonify({
            'status': 'success', 
            'synced_agents': len(my_agents), 
            'newly_claimed': claimed_count,
            'message': f'Synced {len(my_agents)} agents.',
            'errors': errors
        })

    except Exception as e:
        print(f"[Sync] Critical: {e}", flush=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500
