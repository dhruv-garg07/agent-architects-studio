"""
GitMem Routes — Full Pipeline

Data Model:
  - Agents   →  api_agents table   (agent_id, user_id, agent_name, ...)
  - Memories →  gitmem_memories     (agent_id, content, type, importance, ...)
  - Commits  →  gitmem_commits      (agent_id, hash, message, ...)
  - Docs     →  gitmem_documents    (agent_id, folder, filename, ...)
  - Checks   →  gitmem_checkpoints  (agent_id, checkpoint_type, ...)
  - Logs     →  gitmem_activity_logs (agent_id, log_type, action, ...)
  - Refs     →  gitmem_refs         (repo_id = agent_id, ref_name, target_hash)

One agent == one repository. agent_id IS the repo_id.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_required, current_user
import re

from gitmem.core.app import gitmem_app

gitmem_bp = Blueprint(
    'gitmem', __name__,
    url_prefix='/gitmem',
    template_folder='../../templates/gitmem'
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _db():
    return gitmem_app.supabase_client


def _count_chunks_in_chroma(agent_id):
    try:
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        import os
        file_db_path = os.getenv("CHROMA_DATABASE_FILE_DATA")
        if file_db_path:
            file_rag = Agentic_RAG(database=file_db_path, enable_cache=False, enable_monitoring=False)
            file_col = file_rag.wrapper.manager.get_collection(agent_id)
            if file_col:
                cdata = file_col.get(limit=1, include=[])
                return len(cdata.get('ids', []))
    except Exception:
        pass
    return 0

def _get_agent(agent_id, user_id=None):
    """Fetch agent from api_agents by ID or slug. Returns dict or None."""
    if not _db():
        return None
    try:
        import uuid
        is_uuid = False
        try:
            uuid.UUID(agent_id)
            is_uuid = True
        except ValueError:
            pass

        if is_uuid:
            q = _db().table('api_agents').select('*').eq('agent_id', agent_id)
        else:
            q = _db().table('api_agents').select('*').eq('agent_slug', agent_id)
            
        if user_id:
            q = q.eq('user_id', user_id)
            
        res = q.execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Error in _get_agent: {e}")
        return None


def _agent_context(agent_id, agent_raw):
    """Build a consistent agent context dict for templates (used by github_shell)."""
    return {
        'id': (agent_raw or {}).get('agent_id') or agent_id,
        'name': (agent_raw or {}).get('agent_name') or agent_id,
        'slug': (agent_raw or {}).get('agent_slug') or agent_id,
        'description': (agent_raw or {}).get('description') or ((agent_raw or {}).get('metadata') or {}).get('description') or '',
    }


def _count_table(table, col, val):
    if not _db():
        return 0
    try:
        res = _db().table(table).select('*', count='exact').eq(col, val).limit(1).execute()
        return res.count or 0
    except Exception:
        return 0


def _count_table_where(table, filters: dict):
    """Count rows with multiple filters."""
    if not _db():
        return 0
    try:
        q = _db().table(table).select('*', count='exact')
        for col, val in filters.items():
            q = q.eq(col, val)
        res = q.limit(1).execute()
        return res.count or 0
    except Exception:
        return 0


def _ensure_gitmem_repo(agent_id, workspace_id='default'):
    """Ensure a repo exists in gitmem_repos for this agent_id. 
    Required for V2 schema compatibility when agents are created outside GitMem core."""
    if not _db(): return
    try:
        # Check if repo exists
        res = _db().table('gitmem_repos').select('repo_id').eq('repo_id', agent_id).execute()
        if not res.data:
            print(f"[GitMem] Provisioning missing repo for agent {agent_id} in workspace {workspace_id}")
            
            # Ensure workspace exists
            ws_res = _db().table('gitmem_workspaces').select('workspace_id').eq('workspace_id', workspace_id).execute()
            if not ws_res.data:
                try:
                    _db().table('gitmem_workspaces').insert({
                        'workspace_id': workspace_id,
                        'name': 'Default Workspace',
                        'slug': workspace_id,
                        'owner_id': 'system'
                    }).execute()
                except Exception as we:
                    print(f"[GitMem] Workspace insert warning (might exist): {we}")
            
            # Get agent info if possible to populate repo name
            agent = _get_agent(agent_id)
            repo_name = agent.get('agent_name', f"Agent {agent_id[:8]}") if agent else f"Agent {agent_id[:8]}"
            repo_slug = agent.get('agent_slug', agent_id) if agent else agent_id
            owner_id = agent.get('user_id', 'system') if agent else 'system'
            
            _db().table('gitmem_repos').insert({
                'repo_id': agent_id,
                'workspace_id': workspace_id,
                'name': repo_name,
                'slug': repo_slug,
                'owner_id': owner_id,
                'visibility': 'private'
            }).execute()
    except Exception as e:
        print(f"[GitMem] Failed to ensure repo exists: {e}")


def _build_folder_structure(agent_id):
    """
    Build the virtual file-system hierarchy for agent_dashboard.html.
    Returns {memory, documents, checkpoints, logs} with counts.
    """
    # Memory → memories grouped by cognitive type (combines Supabase + ChromaDB)
    memory = {}
    for mtype in ['episodic', 'semantic', 'procedural', 'working', 'state']:
        db_count = _count_table_where('gitmem_memories', {'agent_id': agent_id, 'type': mtype})
        chroma_count = 0
        try:
            raw = gitmem_app.vector_engine.get_agent_vectors(agent_id, limit=200)
            bins = gitmem_app.vector_engine.categorize_vectors(raw)
            chroma_count = len(bins.get(mtype, []))
        except Exception:
            pass
        memory[mtype] = {'count': db_count + chroma_count}

    # Documents → chunks from Chroma DB
    documents = {
        'chunks': {'count': _count_chunks_in_chroma(agent_id)}
    }

    return {
        'memory': memory,
        'documents': documents,
    }


def _build_fs_items(agent_id, virtual_path):
    """
    Build file-browser items for a given virtual path.
    Returns list of {name, type, path, last_modified}.
    """
    items = []
    parts = [p for p in virtual_path.strip('/').split('/') if p]
    depth = len(parts)

    # Root level → show top-level folders
    if depth == 0:
        for name in ['memory', 'docs']:
            items.append({'name': name, 'type': 'directory', 'path': name, 'last_modified': ''})
        return items

    root = parts[0]

    # Level 1: show subfolders
    if depth == 1:
        if root == 'memory':
            for t in ['episodic', 'semantic', 'procedural', 'working', 'state']:
                items.append({'name': t, 'type': 'directory', 'path': f'memory/{t}', 'last_modified': ''})
        elif root in ('docs', 'documents'):
            items.append({'name': 'chunks', 'type': 'directory', 'path': 'docs/chunks', 'last_modified': ''})
        return items

    # Level 2: show actual data as files
    subfolder = parts[1] if len(parts) > 1 else ''
    if root == 'memory' and subfolder:
        # Combine Supabase memories + ChromaDB vectors
        seen_ids = set()
        if _db():
            try:
                res = _db().table('gitmem_memories').select('id,content,created_at') \
                    .eq('agent_id', agent_id).eq('type', subfolder) \
                    .order('created_at', desc=True).limit(50).execute()
                for row in (res.data or []):
                    label = (row.get('content', '') or '')[:60].replace('\n', ' ')
                    items.append({
                        'name': f"{row['id'][:8]} — {label}",
                        'type': 'file',
                        'path': f"memory/{subfolder}/{row['id']}",
                        'last_modified': row.get('created_at', ''),
                    })
                    seen_ids.add(row['id'])
            except Exception:
                pass
        # Also pull from ChromaDB vectors categorized into same type
        try:
            raw = gitmem_app.vector_engine.get_agent_vectors(agent_id, limit=100)
            bins = gitmem_app.vector_engine.categorize_vectors(raw)
            for v in bins.get(subfolder, []):
                if v['id'] not in seen_ids:
                    label = (v.get('content', '') or '')[:60].replace('\n', ' ')
                    items.append({
                        'name': f"{v['id'][:8]} — {label}",
                        'type': 'file',
                        'path': f"memory/{subfolder}/{v['id']}",
                        'last_modified': v.get('created_at', ''),
                    })
        except Exception:
            pass

    elif root in ('docs', 'documents') and subfolder == 'chunks':
        try:
            from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
            import os
            file_db_path = os.getenv("CHROMA_DATABASE_FILE_DATA")
            if file_db_path:
                file_rag = Agentic_RAG(database=file_db_path, enable_cache=False, enable_monitoring=False)
                file_col = file_rag.wrapper.manager.get_collection(agent_id)
                if file_col:
                    cdata = file_col.get(limit=100, include=["metadatas"])
                    ids = cdata.get("ids", [])
                    metas = cdata.get("metadatas", [])
                    for i, cid in enumerate(ids):
                        meta = metas[i] if metas and i < len(metas) else {}
                        fname = meta.get('filename') or meta.get('source') or f'Chunk {i}'
                        items.append({
                            'name': f"{fname} ({cid[:8]}).json",
                            'type': 'file',
                            'path': f"docs/chunks/{cid}",
                            'last_modified': meta.get('created_at', ''),
                        })
        except Exception:
            pass

    return items


def get_sources_status():
    supabase_on = _db() is not None
    chroma_on, chroma_count = False, 0
    try:
        stats = gitmem_app.vector_engine.get_stats()
        chroma_count = stats.get('embeddings', 0) or 0
        chroma_on = gitmem_app.vector_engine.client is not None
    except Exception:
        pass
    return {
        'supabase': supabase_on,
        'chromadb': chroma_on,
        'chromadb_count': chroma_count,
        'mcp': True,
        'local_count': 0,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Landing Page
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/')
@login_required
def landing():
    """
    Smart landing: redirect to the user's first workspace Intelligence page.
    If no workspaces exist, show the workspace creation/onboarding page.
    """
    agents_raw = []
    if _db():
        try:
            res = _db().table('api_agents').select('agent_id, agent_name, agent_slug') \
                .eq('user_id', current_user.get_id()) \
                .order('created_at', desc=True).execute()
            agents_raw = res.data or []
        except Exception as e:
            print(f"[GitMem] landing fetch error: {e}")

    # If user has workspaces, redirect to the first one's Context page
    if agents_raw:
        first_ws = agents_raw[0]
        ws_slug = first_ws.get('agent_id')
        return redirect(url_for('gitmem.hub_context', ws_slug=ws_slug))

    # No workspaces — show the creation page
    return redirect(url_for('gitmem.create_agent_form'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Dashboard — File System View (PRIMARY UI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/advanced')
@login_required
def agent_dashboard(agent_id):
    """Legacy dashboard route — redirects to the new Overview hub."""
    return redirect(url_for('gitmem.hub_overview', ws_slug=agent_id))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Context Explorer (Filesystem Browser)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/w/<ws_slug>/explorer/')
@gitmem_bp.route('/w/<ws_slug>/explorer/<path:virtual_path>')
@login_required
def hub_explorer(ws_slug, virtual_path=''):
    """Unified Context Explorer (virtual filesystem)."""
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    actual_agent_id = agent_raw.get('agent_id')

    items = _build_fs_items(actual_agent_id, virtual_path)
    
    commits = []
    try:
        res = _db().table('gitmem_commits').select('*').eq('agent_id', actual_agent_id).order('timestamp', desc=True).limit(10).execute()
        commits = res.data or []
    except Exception:
        pass

    return render_template(
        'gitmem/hub_explorer.html',
        workspace=agent,
        current_path=virtual_path,
        items=items,
        commits=commits
    )

@gitmem_bp.route('/w/<ws_slug>/sync', methods=['POST'])
@login_required
def hub_sync_memories(ws_slug):
    """Sync memories from ChromaDB to Supabase.
    
    Reads from TWO ChromaDB sources:
    1. gitmem_app.vector_engine (GitMem's VectorEngine — what Explorer/KG reads)
    2. SimpleMem's Agentic_RAG per-agent collections (what /add_memory API writes to)
    
    Maps ChromaDB metadata fields to Supabase gitmem_memories schema:
        memory_type → type, timestamp → created_at, scope → visibility
    """
    import json as _json
    from datetime import datetime as _dt
    
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw:
        flash("Workspace not found.", "error")
        return redirect(url_for('gitmem.landing'))
        
    actual_agent_id = agent_raw.get('agent_id')
    db = _db()
    if not db:
        flash("Supabase not connected.", "error")
        return redirect(url_for('gitmem.hub_explorer', ws_slug=ws_slug))

    # ── 1. Fetch existing Supabase IDs to avoid duplicates ──
    existing_ids = set()
    try:
        res = db.table('gitmem_memories').select('id').eq('agent_id', actual_agent_id).execute()
        existing_ids = {row['id'] for row in (res.data or [])}
        print(f"[Sync] Found {len(existing_ids)} existing memories in Supabase for agent {actual_agent_id}")
    except Exception as e:
        print(f"[Sync] Warning: Could not fetch existing IDs: {e}")

    # ── 2. Ensure repo/workspace FK entries exist ──
    try:
        from gitmem.core.storage.supabase_connector import SupabaseConnector
        supa_conn = SupabaseConnector()
        if not supa_conn._disabled:
            supa_conn._ensure_repo(actual_agent_id, 'default')
            print(f"[Sync] Ensured repo/workspace exist for agent {actual_agent_id}")
    except Exception as e:
        print(f"[Sync] Warning: Could not ensure repo: {e}")

    # ── 2.5 Clean up duplicates before syncing ──
    try:
        from SimpleMem.database.vector_store import VectorStore
        vs = VectorStore(agent_id=actual_agent_id)
        vs.remove_duplicates(0.95)
    except Exception as e:
        print(f"[Sync] Warning: Failed to deduplicate SimpleMem: {e}")
        
    ve = gitmem_app.vector_engine
    if ve:
        try:
            ve.remove_duplicates(actual_agent_id, 0.95)
        except Exception as e:
            print(f"[Sync] Warning: Failed to deduplicate VectorEngine: {e}")

    synced_count = 0
    errors = []

    # ── 3. Sync from GitMem VectorEngine (gitmem_global + per-agent collections) ──
    ve = gitmem_app.vector_engine
    if ve and ve.client:
        chroma_vectors = []
        try:
            chroma_vectors = ve.get_agent_vectors(actual_agent_id, limit=500)
            print(f"[Sync] VectorEngine returned {len(chroma_vectors)} vectors for agent {actual_agent_id}")
        except Exception as e:
            print(f"[Sync] VectorEngine fetch error: {e}")
            errors.append(f"VectorEngine: {e}")

        for v in chroma_vectors:
            vid = v.get('id', '')
            if not vid or vid in existing_ids:
                continue

            meta = v.get('metadata') or {}
            content = v.get('content') or ''

            # Map ChromaDB metadata → Supabase columns
            mem_type = (meta.get('memory_type') or meta.get('type') or 'episodic').lower()
            if mem_type not in ('episodic', 'semantic', 'procedural', 'state'):
                mem_type = 'episodic'
            
            importance = 0.0
            try:
                importance = float(meta.get('importance', 0.0))
            except (ValueError, TypeError):
                pass

            created_at = meta.get('timestamp') or meta.get('created_at') or _dt.now().isoformat()
            visibility = meta.get('scope') or meta.get('visibility') or 'private'

            # Clean metadata for JSONB — must be JSON-serializable
            clean_meta = {}
            for k, val in meta.items():
                if isinstance(val, (str, int, float, bool)) or val is None:
                    clean_meta[k] = val
                else:
                    clean_meta[k] = str(val)

            data = {
                'id': vid,
                'agent_id': actual_agent_id,
                'repo_id': actual_agent_id,
                'workspace_id': 'default',
                'content': content,
                'type': mem_type,
                'importance': importance,
                'visibility': visibility,
                'metadata': clean_meta,
                'created_at': str(created_at),
            }

            try:
                db.table('gitmem_memories').insert(data).execute()
                existing_ids.add(vid)
                synced_count += 1
                print(f"[Sync] ✓ Synced VectorEngine entry {vid[:12]}... ({mem_type})")
            except Exception as e:
                err_str = str(e)
                if '23505' in err_str or 'duplicate' in err_str.lower():
                    existing_ids.add(vid)  # Already exists, skip silently
                else:
                    print(f"[Sync] ✗ Failed to insert {vid[:12]}...: {e}")
                    errors.append(f"{vid[:8]}: {e}")

    # ── 4. Sync from SimpleMem Agentic_RAG per-agent collection ──
    try:
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        import os
        database_path = os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        rag = Agentic_RAG(database=database_path, enable_cache=False, enable_monitoring=False)
        
        try:
            collection = rag.wrapper.manager.get_collection(actual_agent_id)
            chroma_data = collection.get(include=["documents", "metadatas"])
            
            sm_ids = chroma_data.get("ids", [])
            sm_docs = chroma_data.get("documents", [])
            sm_metas = chroma_data.get("metadatas", [])
            print(f"[Sync] SimpleMem Agentic_RAG returned {len(sm_ids)} entries for agent {actual_agent_id}")
            
            for i, sid in enumerate(sm_ids):
                if not sid or sid in existing_ids:
                    continue

                meta = sm_metas[i] if sm_metas and i < len(sm_metas) else {}
                doc = sm_docs[i] if sm_docs and i < len(sm_docs) else ""

                # SimpleMem stores "Content: ..." prefix in documents
                content = doc
                if content.startswith("Content: "):
                    content = content[9:]  # Strip "Content: " prefix
                # Also strip trailing Keywords/Topic lines
                content_lines = content.split("\n")
                clean_lines = [l for l in content_lines if not l.startswith("Keywords:") and not l.startswith("Topic:")]
                content = "\n".join(clean_lines).strip()

                mem_type = (meta.get('memory_type') or meta.get('entry_type') or 'episodic').lower()
                if mem_type not in ('episodic', 'semantic', 'procedural', 'state'):
                    mem_type = 'episodic'

                created_at = meta.get('timestamp') or _dt.now().isoformat()

                clean_meta = {}
                for k, val in meta.items():
                    if isinstance(val, (str, int, float, bool)) or val is None:
                        clean_meta[k] = val
                    else:
                        clean_meta[k] = str(val)

                data = {
                    'id': sid,
                    'agent_id': actual_agent_id,
                    'repo_id': actual_agent_id,
                    'workspace_id': 'default',
                    'content': content or "(empty)",
                    'type': mem_type,
                    'importance': 0.5,
                    'visibility': 'private',
                    'metadata': clean_meta,
                    'created_at': str(created_at),
                }

                try:
                    db.table('gitmem_memories').insert(data).execute()
                    existing_ids.add(sid)
                    synced_count += 1
                    print(f"[Sync] ✓ Synced SimpleMem entry {sid[:12]}... ({mem_type})")
                except Exception as e:
                    err_str = str(e)
                    if '23505' in err_str or 'duplicate' in err_str.lower():
                        existing_ids.add(sid)
                    else:
                        print(f"[Sync] ✗ Failed to insert SimpleMem {sid[:12]}...: {e}")
                        errors.append(f"SM-{sid[:8]}: {e}")
        except Exception as e:
            print(f"[Sync] SimpleMem collection not found or error: {e}")
    except Exception as e:
        print(f"[Sync] Could not import/init Agentic_RAG: {e}")

    # ── 5. Report result ──
    if errors:
        flash(f"Sync done: {synced_count} synced, {len(errors)} errors. Check terminal.", "warning")
    elif synced_count > 0:
        flash(f"✓ Sync complete! Pushed {synced_count} missing memories to Supabase.", "success")
    else:
        flash("All memories already in sync — nothing new to push.", "info")
    
    print(f"[Sync] === COMPLETE: {synced_count} synced, {len(errors)} errors ===")
    return redirect(url_for('gitmem.hub_explorer', ws_slug=ws_slug))



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# File View (single memory/document)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/w/<ws_slug>/file/')
@gitmem_bp.route('/w/<ws_slug>/file/<path:virtual_path>')
@login_required
def hub_file_view(ws_slug, virtual_path=''):
    """Unified file viewer and editor."""
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))

    agent = _agent_context(ws_slug, agent_raw)
    actual_agent_id = agent_raw.get('agent_id')

    # Parse path to figure out source: memory/{id}, docs/{folder}/{id}
    parts = [p for p in virtual_path.strip('/').split('/') if p]
    file_content = 'Item not found'
    metadata = {}

    if len(parts) >= 3:
        root, subfolder, item_id = parts[0], parts[1], parts[2]
        try:
            if root == 'memory':
                # First try Supabase
                found_in_db = False
                if _db():
                    res = _db().table('gitmem_memories').select('*').eq('id', item_id).execute()
                    if res.data:
                        row = res.data[0]
                        file_content = row.get('content', '')
                        metadata = row.get('metadata', {}) if isinstance(row.get('metadata'), dict) else {}
                        metadata.update({
                            'id': row.get('id'),
                            'type': row.get('type'),
                            'importance': row.get('importance'),
                            'created_at': row.get('created_at')
                        })
                        found_in_db = True
                
                # If not in Supabase, try ChromaDB
                if not found_in_db:
                    v = gitmem_app.vector_engine.get_vector(item_id, actual_agent_id)
                    if v:
                        file_content = v.get('content', '')
                        metadata = v.get('metadata', {})
                        metadata.update({'id': v.get('id')})
            elif root in ('docs', 'documents'):
                try:
                    from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
                    import os
                    file_db_path = os.getenv("CHROMA_DATABASE_FILE_DATA")
                    if file_db_path:
                        file_rag = Agentic_RAG(database=file_db_path, enable_cache=False, enable_monitoring=False)
                        file_col = file_rag.wrapper.manager.get_collection(actual_agent_id)
                        if file_col:
                            cdata = file_col.get(ids=[item_id], include=["documents", "metadatas"])
                            if cdata and cdata.get('ids'):
                                file_content = cdata['documents'][0] if cdata.get('documents') else ''
                                metadata = cdata['metadatas'][0] if cdata.get('metadatas') else {}
                                metadata.update({'id': item_id, 'filename': metadata.get('filename') or metadata.get('source')})
                except Exception:
                    pass
            elif root == 'vectors':
                v = gitmem_app.vector_engine.get_vector(item_id, actual_agent_id)
                if v:
                    file_content = v.get('content', '')
                    metadata = v.get('metadata', {})
            elif root == 'checkpoints':
                res = _db().table('gitmem_checkpoints').select('*').eq('id', item_id).execute()
                if res.data:
                    row = res.data[0]
                    file_content = row.get('data', row.get('content', 'No content available'))
                    metadata = row.get('metadata', {}) if isinstance(row.get('metadata'), dict) else {}
                    metadata.update({'id': row.get('id'), 'name': row.get('name')})
            elif root == 'logs':
                res = _db().table('gitmem_activity_logs').select('*').eq('id', item_id).execute()
                if res.data:
                    row = res.data[0]
                    file_content = f"{row.get('action', '')} {row.get('resource_type', '')}\nID: {row.get('id')}"
                    metadata = row
        except Exception as e:
            file_content = f"Error retrieving item: {e}"

    if request.args.get('raw'):
        return Response(file_content, mimetype='text/plain')

    return render_template(
        'gitmem/hub_file_view.html',
        workspace=agent,
        path=virtual_path,
        content=file_content,
        metadata=metadata
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Commit Log
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/advanced/history')
@login_required
def agent_history(agent_id):
    """Unified history view with branch management and commit graph."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        flash("Repository not found.", "error")
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)

    current_branch = request.args.get('branch', 'main')
    
    # 1. Fetch Branches
    branches = []
    try:
        branches_raw = gitmem_app.vcs.branch_manager.list_branches(agent_id)
        for b in branches_raw:
            commit_meta = None
            if b.get('target_hash') and b['target_hash'] != 'HEAD':
                try:
                    res = _db().table('gitmem_commits').select('*').eq('hash', b['target_hash']).limit(1).execute()
                    if res.data: commit_meta = res.data[0]
                except: pass
            branches.append({
                'name': b['ref_name'],
                'hash': b['target_hash'],
                'commit': commit_meta
            })
        if not any(b['name'] == 'main' for b in branches):
            branches.insert(0, {'name': 'main', 'hash': 'HEAD', 'commit': None})
    except Exception:
        branches = [{'name': 'main', 'hash': 'HEAD', 'commit': None}]

    # 2. Fetch Commits
    commits = []
    try:
        db = _db()
        if db:
            res = db.table('gitmem_commits').select('*').eq('repo_id', agent_id).order('timestamp', desc=True).limit(100).execute()
            commits = res.data or []
    except Exception: pass

    # 3. Graph Logic (Assign tracks/colors)
    # Simple track allocation: each branch gets a track
    branch_tracks = {b['name']: i for i, b in enumerate(branches)}
    # Map commit hash to branch name if it's a branch tip
    tip_map = {b['hash']: b['name'] for b in branches if b['hash'] != 'HEAD'}
    
    for c in commits:
        c['track'] = branch_tracks.get(tip_map.get(c['hash'], 'main'), 0)
        c['is_tip'] = c['hash'] in tip_map

    memory_count = _count_table('gitmem_memories', 'agent_id', agent_id)
    commit_count = len(commits)

    import json
    commits_json = json.dumps([{'sha': c['hash'], 'message': c.get('message',''), 'timestamp': c.get('timestamp',''), 'author_id': c.get('author_id','')} for c in commits])

    return render_template(
        'history.html',
        agent=agent,
        commits=commits,
        commits_json=commits_json,
        branches=branches,
        current_branch=current_branch,
        memory_count=memory_count,
        commit_count=commit_count,
        sources=get_sources_status(),
    )


@gitmem_bp.route('/agent/<agent_id>/advanced/commits')
@login_required
def agent_commits(agent_id):
    """Commit history page (Redirecting to unified history)."""
    return redirect(url_for('gitmem.agent_history', agent_id=agent_id, branch=request.args.get('branch', 'main')))


@gitmem_bp.route('/agent/<agent_id>/advanced/branches_view')
@login_required
def agent_branches(agent_id):
    """Branches view (Redirecting to unified history)."""
    return redirect(url_for('gitmem.agent_history', agent_id=agent_id))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Diff Viewer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/advanced/diffs')
@login_required
def agent_diffs(agent_id):
    """Diff viewer — redirects to the unified history page which now includes the diff viewer."""
    return redirect(url_for('gitmem.agent_history', agent_id=agent_id))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Placeholder pages (Issues, Pulls, Settings, Wiki, etc.)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/advanced/pulls')
@login_required
def pulls(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    return render_template('pulls.html', agent=agent, pulls=[], sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/advanced/issues')
@login_required
def issues(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    return render_template('issues.html', agent=agent, issues=[], sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/advanced/settings')
@login_required
def settings(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)
    # Get workspace_id for team management (default workspace if not set)
    workspace_id = agent_raw.get('workspace_id', 'default')
    # Branches for shell
    current_branch = request.args.get('branch', 'main')
    branches = []
    try:
        branches_raw = gitmem_app.vcs.branch_manager.list_branches(agent_id)
        branches = [b.get('ref_name') for b in branches_raw if b.get('ref_name')]
        if not branches or 'main' not in branches:
            branches.insert(0, 'main')
    except Exception:
        branches = ['main']

    return render_template('settings.html', agent=agent, workspace_id=workspace_id, branches=branches, current_branch=current_branch, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/advanced/wiki')
@login_required
def wiki(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    return render_template('wiki.html', agent=agent, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/advanced/checkpoints')
@login_required
def agent_checkpoints(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    checkpoints = []
    if _db():
        try:
            res = _db().table('gitmem_checkpoints').select('*') \
                .eq('agent_id', agent_id).order('created_at', desc=True).limit(50).execute()
            checkpoints = res.data or []
        except Exception:
            pass
    return render_template('checkpoints.html', agent=agent, checkpoints=checkpoints, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/advanced/logs')
@login_required
def agent_logs(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    logs = []
    if _db():
        try:
            res = _db().table('gitmem_activity_logs').select('*') \
                .eq('agent_id', agent_id).order('created_at', desc=True).limit(100).execute()
            logs = res.data or []
        except Exception:
            pass
    return render_template('activity_logs.html', agent=agent, logs=logs, sources=get_sources_status())


# Backward compat: /repo/<id> → /agent/<id>
@gitmem_bp.route('/repo/<repo_id>')
@login_required
def repo_dashboard(repo_id):
    return redirect(url_for('gitmem.agent_dashboard', agent_id=repo_id))
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Workspace Views (Mission Control)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/w/<ws_slug>/')
@login_required
def hub_workspace(ws_slug):
    """Workspace root redirects to Agents page (formerly Context)."""
    return redirect(url_for('gitmem.hub_agents', ws_slug=ws_slug))


@gitmem_bp.route('/w/<ws_slug>/overview')
@login_required
def hub_overview(ws_slug):
    """Overview page — redirects to Agents since Mission Control merged with Agents."""
    return redirect(url_for('gitmem.hub_agents', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/context')
@login_required
def hub_context(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    
    actual_agent_id = agent_raw.get('agent_id')

    # Fetch all user's agents for the agent selector
    all_agents = []
    try:
        res = _db().table('api_agents').select('agent_id, agent_name, agent_slug, status') \
            .eq('user_id', current_user.get_id()) \
            .order('created_at', desc=True).execute()
        all_agents = res.data or []
    except Exception as e:
        print(f"Error fetching all agents: {e}")

    # Fetch memories for this agent
    memories = []
    try:
        res = _db().table('gitmem_memories').select('*') \
            .eq('agent_id', actual_agent_id) \
            .order('created_at', desc=True).limit(100).execute()
        memories = res.data or []
    except Exception as e:
        print(f"Error fetching memories: {e}")

    # Count by type
    type_counts = {}
    for m in memories:
        t = m.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    # Vector stats
    vector_count = 0
    try:
        stats = gitmem_app.vector_engine.get_agent_stats(actual_agent_id)
        vector_count = stats.get('embeddings', 0) or 0
    except Exception as e:
        print(f"Error fetching vector stats: {e}")

    # Document count
    doc_count = _count_chunks_in_chroma(actual_agent_id)

    # Fetch documents for this agent natively from ChromaDB
    documents = []
    try:
        import os
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        file_db_path = os.getenv("CHROMA_DATABASE_FILE_DATA")
        if file_db_path:
            file_rag = Agentic_RAG(database=file_db_path, enable_cache=False, enable_monitoring=False)
            file_col = file_rag.wrapper.manager.get_collection(actual_agent_id)
            if file_col:
                cdata = file_col.get(limit=100, include=["documents", "metadatas"])
                f_ids = cdata.get("ids", [])
                f_docs = cdata.get("documents", [])
                f_metas = cdata.get("metadatas", [])
                for i, cid in enumerate(f_ids):
                    meta = f_metas[i] if f_metas and i < len(f_metas) else {}
                    filename = meta.get('filename') or meta.get('source') or f'Chunk {i}'
                    content = f_docs[i] if f_docs and i < len(f_docs) else ''
                    doc_item = {
                        'id': cid,
                        'filename': filename,
                        'content': content,
                        'created_at': meta.get('created_at', '')
                    }
                    documents.append(doc_item)
    except Exception as e:
        print(f"Error fetching documents from Chroma: {e}")

    # Commit count
    commit_count = _count_table('gitmem_commits', 'agent_id', actual_agent_id)

    import json
    
    # Combine memories and documents for the Knowledge Graph nodes
    graph_nodes = []
    for m in memories:
        graph_nodes.append({
            'id': m.get('id',''),
            'content': (m.get('content','') or '')[:200],
            'type': m.get('type',''),
            'importance': m.get('importance', 0.5),
            'tags': m.get('tags', []),
            'created_at': (m.get('created_at','') or '')[:16],
        })
    for d in documents:
        graph_nodes.append({
            'id': d.get('id',''),
            'content': (d.get('content','') or '')[:200],
            'type': 'document',
            'importance': 0.5,
            'tags': [],
            'created_at': d.get('created_at','')[:16],
        })

    return render_template('gitmem/hub_knowledge_studio.html',
        workspace=agent,
        memories=memories,
        type_counts=type_counts,
        total_memories=len(memories),
        vector_count=vector_count,
        doc_count=doc_count,
        documents=documents,
        commit_count=commit_count,
        all_agents=all_agents,
        memories_json=json.dumps(graph_nodes)
    )

@gitmem_bp.route('/w/<ws_slug>/context/<category>')
@login_required
def hub_context_category(ws_slug, category):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_context_category.html', workspace=agent, category=category)

@gitmem_bp.route('/w/<ws_slug>/history')
@login_required
def hub_history(ws_slug):
    """Workspace-level version history — commits, branches, diffs."""
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)

    actual_agent_id = agent_raw.get('agent_id')
    current_branch = request.args.get('branch', 'main')

    # Fetch Branches
    branches = []
    try:
        branches_raw = gitmem_app.vcs.branch_manager.list_branches(actual_agent_id)
        for b in branches_raw:
            commit_meta = None
            if b.get('target_hash') and b['target_hash'] != 'HEAD':
                try:
                    res = _db().table('gitmem_commits').select('*').eq('hash', b['target_hash']).limit(1).execute()
                    if res.data: commit_meta = res.data[0]
                except: pass
            branches.append({
                'name': b['ref_name'],
                'hash': b['target_hash'],
                'commit': commit_meta
            })
        if not any(b['name'] == 'main' for b in branches):
            branches.insert(0, {'name': 'main', 'hash': 'HEAD', 'commit': None})
    except Exception:
        branches = [{'name': 'main', 'hash': 'HEAD', 'commit': None}]

    # Fetch Commits
    commits = []
    try:
        db = _db()
        if db:
            res = db.table('gitmem_commits').select('*').eq('repo_id', actual_agent_id).order('timestamp', desc=True).limit(100).execute()
            commits = res.data or []
    except Exception: pass

    # Graph Logic (Assign tracks/colors)
    branch_tracks = {b['name']: i for i, b in enumerate(branches)}
    tip_map = {b['hash']: b['name'] for b in branches if b['hash'] != 'HEAD'}
    for c in commits:
        c['track'] = branch_tracks.get(tip_map.get(c['hash'], 'main'), 0)
        c['is_tip'] = c['hash'] in tip_map

    memory_count = _count_table('gitmem_memories', 'agent_id', actual_agent_id)
    commit_count = len(commits)

    import json
    commits_json = json.dumps([{'sha': c['hash'], 'message': c.get('message',''), 'timestamp': c.get('timestamp',''), 'author_id': c.get('author_id','')} for c in commits])

    return render_template('gitmem/hub_changes.html',
        workspace=agent,
        commits=commits,
        commits_json=commits_json,
        branches=branches,
        current_branch=current_branch,
        memory_count=memory_count,
        commit_count=commit_count,
    )

@gitmem_bp.route('/w/<ws_slug>/agents')
@login_required
def hub_agents(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_agents.html', workspace=agent)

@gitmem_bp.route('/w/<ws_slug>/integrations')
@login_required
def hub_integrations(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_integrations.html', workspace=agent)

@gitmem_bp.route('/w/<ws_slug>/governance')
@login_required
def hub_governance(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_trust_center.html', workspace=agent)

@gitmem_bp.route('/w/<ws_slug>/search')
@login_required
def hub_search(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_search.html', workspace=agent)

@gitmem_bp.route('/w/<ws_slug>/chat')
@login_required
def hub_chat(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_chat.html', workspace=agent)

@gitmem_bp.route('/w/<ws_slug>/permissions')
@login_required
def hub_permissions(ws_slug):
    return redirect(url_for('gitmem.hub_governance', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/audit')
@login_required
def hub_audit(ws_slug):
    return redirect(url_for('gitmem.hub_governance', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/branches')
@login_required
def hub_branches(ws_slug):
    return redirect(url_for('gitmem.hub_history', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/activity')
@login_required
def hub_activity(ws_slug):
    """Activity is now part of the Overview feed."""
    return redirect(url_for('gitmem.hub_overview', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/analytics')
@login_required
def hub_analytics(ws_slug):
    """Analytics is now part of the Overview page."""
    return redirect(url_for('gitmem.hub_overview', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/intelligence')
@login_required
def hub_intelligence_legacy(ws_slug):
    """Legacy intelligence route redirects to overview."""
    return redirect(url_for('gitmem.hub_overview', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/connections')
@login_required
def hub_connections(ws_slug):
    """Connections page — alias for integrations."""
    return redirect(url_for('gitmem.hub_integrations', ws_slug=ws_slug))

@gitmem_bp.route('/w/<ws_slug>/settings')
@login_required
def hub_settings(ws_slug):
    agent_raw = _get_agent(ws_slug, user_id=current_user.get_id())
    if not agent_raw: return redirect(url_for('gitmem.landing'))
    agent = _agent_context(ws_slug, agent_raw)
    return render_template('gitmem/hub_settings.html', workspace=agent)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Legacy Redirects (301 Permanent)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>')
def legacy_agent_dashboard(agent_id):
    return redirect(url_for('gitmem.hub_workspace', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/memories')
def legacy_agent_memories(agent_id):
    return redirect(url_for('gitmem.hub_context', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/documents')
def legacy_agent_documents(agent_id):
    return redirect(url_for('gitmem.hub_context_category', ws_slug=agent_id, category='documents'), code=301)

@gitmem_bp.route('/agent/<agent_id>/sources')
def legacy_agent_sources(agent_id):
    return redirect(url_for('gitmem.hub_integrations', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/history')
def legacy_agent_history(agent_id):
    return redirect(url_for('gitmem.hub_activity', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/settings')
def legacy_agent_settings(agent_id):
    return redirect(url_for('gitmem.hub_settings', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/checkpoints')
def legacy_agent_checkpoints(agent_id):
    return redirect(url_for('gitmem.hub_activity', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/logs')
def legacy_agent_logs(agent_id):
    return redirect(url_for('gitmem.hub_activity', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/pulls')
def legacy_agent_pulls(agent_id):
    return redirect(url_for('gitmem.hub_governance', ws_slug=agent_id), code=301)

@gitmem_bp.route('/agent/<agent_id>/issues')
def legacy_agent_issues(agent_id):
    return redirect(url_for('gitmem.hub_governance', ws_slug=agent_id), code=301)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Create Agent
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/new', methods=['GET'])
@login_required
def create_agent_form():
    # Fetch user's workspaces for the selector
    workspaces = []
    if _db():
        try:
            mem_res = _db().table('gitmem_workspace_members').select('workspace_id, role').eq('user_id', current_user.get_id()).execute()
            if mem_res.data:
                ws_ids = [m['workspace_id'] for m in mem_res.data]
                ws_res = _db().table('gitmem_workspaces').select('*').in_('workspace_id', ws_ids).execute()
                workspaces = ws_res.data or []
        except Exception:
            pass
    ws_id = request.args.get('workspace_id', '')
    return render_template('create_agent.html', workspaces=workspaces, selected_workspace_id=ws_id, sources=get_sources_status())


@gitmem_bp.route('/api/create-agent', methods=['POST'])
@login_required
def api_create_agent():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    agent_slug = re.sub(r'[^a-z0-9\-_\.]', '-', data.get('agent_id', '').strip().lower()).strip('-')
    agent_name = data.get('name', '').strip() or agent_slug
    description = data.get('description', '').strip()

    if not agent_slug:
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({"error": "Agent ID is required."}), 400
        flash("Agent ID is required.", "error")
        return redirect(url_for('gitmem.create_agent_form'))

    if not _db():
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({"error": "Database disconnected."}), 500
        flash("Database disconnected.", "error")
        return redirect(url_for('gitmem.create_agent_form'))

    workspace_id = data.get('workspace_id', '').strip()

    try:
        from backend_examples.python.services.api_agents import ApiAgentsService
        svc = ApiAgentsService()
        agent_id, _ = svc.create_agent(
            user_id=current_user.get_id(),
            agent_name=agent_name,
            agent_slug=agent_slug,
            description=description,
            permissions={"read": True, "write": True},
            limits={"max_memories": 10000},
            metadata={"capabilities": [], "status": "active", "workspace_id": workspace_id},
        )
        # Create default branch using the VCS facade (handles repo provisioning)
        try:
            gitmem_app.vcs.branch(agent_id, 'main', 'HEAD', current_user.get_id(), workspace_id=workspace_id)
        except Exception as e:
            print(f"[GitMem] Initial branch creation warning: {e}")

        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({"status": "success", "agent_id": agent_id, "agent_name": agent_name})

        flash(f"Repository '{agent_name}' created.", "success")
        return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))
    except Exception as e:
        if request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({"error": f"Failed to create repository: {e}"}), 500
        flash(f"Failed to create repository: {e}", "error")
        return redirect(url_for('gitmem.create_agent_form'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/workspace_stats')
@login_required
def api_workspace_stats():
    """Returns company-wide or agent-wide stats.
    If ?ws_slug is provided, returns stats for that specific agent.
    Otherwise, returns aggregated stats for all user agents.
    """
    try:
        user_id = current_user.get_id()
        db = _db()
        if not db:
            return jsonify({"error": "Database unavailable"}), 503

        target_slug = request.args.get('ws_slug')
        
        # 1. Total Agents & Active Agents
        if target_slug:
            # Agent-wide
            agents_res = db.table('api_agents').select('agent_id, agent_slug, status').eq('user_id', user_id).eq('agent_slug', target_slug).execute()
        else:
            # User-wide
            agents_res = db.table('api_agents').select('agent_id, agent_slug, status').eq('user_id', user_id).execute()
            
        agents = agents_res.data or []
        total_agents = len(agents)
        active_agents = sum(1 for a in agents if a.get('status') == 'active')
        
        # 2. Total Tool Calls & Memories Generated
        agent_ids = [a['agent_id'] for a in agents]
        agent_slugs = [a['agent_slug'] for a in agents]
        
        total_tool_calls = 0
        total_memories = 0
        
        if agent_ids:
            # Tool calls (from activity logs)
            # Some queries use UUID (agent_id) and some use slug. 
            # We will try with IDs first.
            try:
                logs_res = db.table('gitmem_activity_logs').select('id, action').in_('agent_id', agent_ids).execute()
                logs = logs_res.data or []
                total_tool_calls += sum(1 for log in logs if 'tool' in str(log.get('action', '')).lower() or 'decision' in str(log.get('action', '')).lower())
            except Exception as e:
                # Fallback to slugs
                logs_res = db.table('gitmem_activity_logs').select('id, action').in_('agent_id', agent_slugs).execute()
                logs = logs_res.data or []
                total_tool_calls += sum(1 for log in logs if 'tool' in str(log.get('action', '')).lower() or 'decision' in str(log.get('action', '')).lower())

            # Memories
            try:
                memories_res = db.table('gitmem_memories').select('id').in_('agent_id', agent_ids).execute()
                total_memories += len(memories_res.data or [])
            except Exception:
                memories_res = db.table('gitmem_memories').select('id').in_('agent_id', agent_slugs).execute()
                total_memories += len(memories_res.data or [])
        
        return jsonify({
            "status": "success",
            "stats": {
                "total_agents": total_agents,
                "active_agents": active_agents,
                "total_tool_calls": total_tool_calls,
                "total_memories": total_memories
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ==========================================
# RAG Document Ingestion & Retrieval Endpoints
# (Mirrors api_manhattan.py)
# ==========================================

@gitmem_bp.route('/api/add_document', methods=['POST'])
@login_required
def api_add_document():
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    document_content = data.get('documents')
    ids = data.get('ids', [])
    metadata = data.get('metadata', {})
    
    if not agent_id or not document_content or not ids:
        return jsonify({'error': 'agent_id, documents, and ids are required'}), 400
    
    if len(document_content) != len(ids):
        return jsonify({'error': 'Length of documents and ids must be the same'}), 400

    try:
        from utils.chunking import UnifiedChunker
        import logging
        import os
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        
        chunking_mode = data.get('chunking_mode', 'fast')
        chunker = UnifiedChunker(mode=chunking_mode)
        
        all_chunk_ids = []
        all_chunk_docs = []
        all_chunk_metas = []
        
        for i, doc in enumerate(document_content):
            doc_id = ids[i]
            meta = metadata if metadata else {}
            
            chunks = chunker.chunk_text(doc, metadata=meta)
            for chunk_idx, chunk in enumerate(chunks):
                all_chunk_ids.append(f"{doc_id}_chunk_{chunk_idx}")
                all_chunk_docs.append(chunk['text'])
                all_chunk_metas.append(chunk['metadata'])
                
        if not all_chunk_docs:
            return jsonify({'error': 'No chunks generated from documents'}), 400

        logging.info(f"[GitMem Ingestion] Agent {agent_id}: Ingesting {len(all_chunk_docs)} chunks (mode: {chunking_mode}). Zero LLM calls made.")
        
        rag = Agentic_RAG(database=os.getenv("CHROMA_DATABASE_FILE_DATA"))
        rag.add_docs(
            agent_ID=agent_id,
            ids=all_chunk_ids,
            documents=all_chunk_docs,
            metadatas=all_chunk_metas
        )
        
        import datetime
        db = _db()
        if db:
            base_filename = metadata.get('filename') or metadata.get('title') or "Untitled Document"
            for i, doc_id in enumerate(ids):
                filename = f"{base_filename} ({i+1})" if len(ids) > 1 else base_filename
                try:
                    db.table('gitmem_documents').insert({
                        'id': doc_id,
                        'agent_id': agent_id,
                        'filename': filename,
                        'folder': 'uploads',
                        'created_at': datetime.datetime.utcnow().isoformat()
                    }).execute()
                except Exception as e:
                    logging.error(f"Failed to insert doc {doc_id} to Supabase: {e}")
                    
        return jsonify({'ok': True, 'message': 'documents_added', 'chunks_count': len(all_chunk_docs)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500  

@gitmem_bp.route('/api/search_documents', methods=['POST'])
@login_required
def api_search_documents():
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    query = data.get('query')
    top_k = data.get('top_k', 5)

    if not agent_id or not query:
        return jsonify({'error': 'agent_id and query are required'}), 400

    try:
        import logging
        import os
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        
        rag = Agentic_RAG(database=os.getenv("CHROMA_DATABASE_FILE_DATA"))
        retrieve_k = top_k * 2
        results = rag.search_agent_collection(
            agent_ID=agent_id,
            query=query,
            n_results=retrieve_k
        )
        
        if not results:
            return jsonify({'results': [], 'synthesized_answer': 'No relevant documents found to answer the query.'}), 200
            
        from utils.reranking import Reranker
        reranker = Reranker()
        
        docs_to_rerank = [{'text': r.get('document', r.get('text', '')), 'metadata': r.get('metadata', {})} for r in results]
        reranked_docs = reranker.rerank(query=query, documents=docs_to_rerank, top_k=top_k)
        
        from SimpleMem.utils.llm_client import LLMClient
        from SimpleMem.core.document_synthesizer import DocumentSynthesizer
        
        llm_client = LLMClient()
        synthesizer = DocumentSynthesizer(llm_client=llm_client)
        logging.info(f"[GitMem Retrieval] Agent {agent_id}: Synthesizing answer for query '{query}' using {len(reranked_docs)} chunks.")
        
        synthesized_answer = synthesizer.synthesize(query=query, chunks=reranked_docs)
        
        return jsonify({
            'results': reranked_docs,
            'synthesized_answer': synthesized_answer
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '').strip()
    agent_id = request.args.get('repo_id') or request.args.get('agent_id')
    if not query or not agent_id:
        return jsonify({"error": "Missing q and repo_id/agent_id"}), 400

    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403

    try:
        result = gitmem_app.retrieval.retrieve(query=query, repo_id=agent_id, agent_id=agent_id, max_tokens=2000)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/memory', methods=['POST'])
@login_required
def api_add_memory():
    """Add a memory to an agent."""
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    content = data.get('content', '').strip()
    mtype = data.get('type', 'episodic')
    importance = float(data.get('importance', 0.5))
    
    tags = data.get('tags', [])
    topic = data.get('topic', '')
    storage_bin = data.get('storage_bin', 'memory')
    attributes = data.get('attributes', {})

    if not agent_id or not content:
        return jsonify({"error": "agent_id and content required"}), 400

    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403

    try:
        # Ensure V2 repo structure exists
        _ensure_gitmem_repo(agent_id)

        from gitmem.core.models import MemoryItem
        import uuid
        mem = MemoryItem(
            id=str(uuid.uuid4()),
            repo_id=agent_id,
            workspace_id='default',
            agent_id=agent_id,
            type=mtype,
            content=content,
            importance=importance,
            tags=tags,
            metadata={
                'topic': topic,
                'storage_bin': storage_bin,
                **attributes
            }
        )
        db = _db()
        if not db:
            return jsonify({"error": "Database unavailable"}), 503
        db.table('gitmem_memories').insert(mem.to_dict()).execute()

        # Also index in vector store (best-effort)
        try:
            gitmem_app.vector_engine.add_memory(mem)
        except Exception:
            pass

        return jsonify({"status": "success", "id": mem.id})
    except Exception as e:
        print(f"[GitMem] Memory insert failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/memory/<memory_id>', methods=['DELETE'])
@login_required
def api_delete_memory(memory_id):
    """Delete a memory."""
    db = _db()
    if not db:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        res = db.table('gitmem_memories').select('agent_id').eq('id', memory_id).execute()
        if not res.data:
            return jsonify({"error": "Not found"}), 404
        agent_id = res.data[0]['agent_id']
        if not _get_agent(agent_id, user_id=current_user.get_id()):
            return jsonify({"error": "Access denied"}), 403

        db.table('gitmem_memories').delete().eq('id', memory_id).execute()
        # Clean up vector index
        try:
            gitmem_app.vector_engine.delete_memory(memory_id, agent_id=agent_id)
        except Exception:
            pass  # Vector cleanup is best-effort
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/memory/<memory_id>', methods=['PUT'])
@login_required
def api_update_memory(memory_id):
    """Update an existing memory's content, type, importance, or tags."""
    data = request.get_json(silent=True) or {}
    db = _db()
    if not db:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        res = db.table('gitmem_memories').select('*').eq('id', memory_id).execute()
        if not res.data:
            return jsonify({"error": "Not found"}), 404
        existing = res.data[0]
        agent_id = existing['agent_id']
        if not _get_agent(agent_id, user_id=current_user.get_id()):
            return jsonify({"error": "Access denied"}), 403

        # Build update payload from provided fields only
        updates = {}
        if 'content' in data:
            updates['content'] = data['content'].strip()
        if 'type' in data and data['type'] in ('episodic', 'semantic', 'procedural', 'state'):
            updates['type'] = data['type']
        if 'importance' in data:
            updates['importance'] = max(0.0, min(1.0, float(data['importance'])))
        if 'tags' in data:
            updates['tags'] = data['tags'] if isinstance(data['tags'], list) else []

        if not updates:
            return jsonify({"error": "No fields to update"}), 400

        from datetime import datetime
        updates['updated_at'] = datetime.utcnow().isoformat()
        db.table('gitmem_memories').update(updates).eq('id', memory_id).execute()

        # Re-index in vector if content changed
        if 'content' in updates:
            try:
                from gitmem.core.models import MemoryItem
                updated = {**existing, **updates}
                mem = MemoryItem(**{k: v for k, v in updated.items() if k != 'embedding'})
                gitmem_app.vector_engine.delete_memory(memory_id, agent_id=agent_id)
                gitmem_app.vector_engine.add_memory(mem)
            except Exception:
                pass  # Vector re-index is best-effort

        return jsonify({"status": "success", "id": memory_id})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/documents/<agent_id>/upload', methods=['POST'])
@login_required
def api_document_upload(agent_id):
    """Upload a document (text file) to an agent's document store."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403

    file = request.files.get('file')
    folder = request.form.get('folder', 'uploads')
    description = request.form.get('description', '')

    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400

    try:
        import uuid
        from datetime import datetime
        content = file.read().decode('utf-8', errors='replace')
        doc = {
            'id': str(uuid.uuid4()),
            'agent_id': agent_id,
            'folder': folder,
            'filename': file.filename,
            'content_type': file.content_type or 'text/plain',
            'size_bytes': len(content.encode('utf-8')),
            'content': content,
            'description': description,
            'storage_path': f'{agent_id}/{folder}/{file.filename}',
            'created_at': datetime.utcnow().isoformat(),
        }
        db = _db()
        if not db:
            return jsonify({"error": "Database unavailable"}), 503
        db.table('gitmem_documents').insert(doc).execute()
        return jsonify({"status": "success", "id": doc['id'], "filename": file.filename}), 201
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/documents/<agent_id>/<doc_id>', methods=['DELETE'])
@login_required
def api_document_delete(agent_id, doc_id):
    """Delete a document from an agent's store."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    db = _db()
    if not db:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        db.table('gitmem_documents').delete().eq('id', doc_id).eq('agent_id', agent_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/sync-sources', methods=['POST'])
@login_required
def api_sync_sources():
    try:
        stats = gitmem_app.vector_engine.get_stats()
        return jsonify({"status": "ok", "stats": stats})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Knowledge Graph API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cosine_sim(a, b):
    """Compute cosine similarity between two float lists. Returns 0-1."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _build_graph_data(memories, vectors_with_embeddings):
    """
    Build a semantically-aware knowledge graph.

    Nodes: memories + vectors, colored by type.
    Edges (5 kinds):
      1. semantic — cosine similarity > threshold (strength = similarity score)
      2. tag      — shared tags between memories
      3. provenance — parent/source chains
      4. related  — explicit metadata.related_ids
      5. cluster  — lightweight type grouping
    """
    TYPE_COLORS = {
        'episodic':   '#3b82f6',
        'semantic':   '#8b5cf6',
        'procedural': '#10b981',
        'state':      '#6b7280',
        'vector':     '#f59e0b',
        'document':   '#06b6d4',
        'docs':       '#06b6d4',
    }

    nodes = []
    id_set = set()
    tag_index = {}
    type_index = {}
    embeddings = {}  # id → embedding vector (for semantic edges)

    # ── Add memory nodes ──────────────────────────────────────────
    for m in memories:
        mid = m.get('id', '')
        if not mid or mid in id_set:
            continue
        id_set.add(mid)

        mtype = (m.get('type') or 'episodic').lower()
        importance = 0.5
        try:
            importance = float(m.get('importance') or 0.5)
        except (ValueError, TypeError):
            pass
        content = (m.get('content') or '')
        tags = m.get('tags') or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]

        nodes.append({
            'id':         mid,
            'label':      content[:100].replace('\n', ' '),
            'group':      mtype,
            'color':      TYPE_COLORS.get(mtype, '#6b7280'),
            'importance': importance,
            'val':        3 + (importance * 10),
            'tags':       tags,
            'created_at': (m.get('created_at') or '')[:10],
        })

        for tag in tags:
            t = tag.lower().strip()
            if t:
                tag_index.setdefault(t, []).append(mid)
        type_index.setdefault(mtype, []).append(mid)

    # ── Add vector nodes (from ChromaDB with embeddings) ──────────
    for v in vectors_with_embeddings:
        vid = v.get('id', '')
        if not vid or vid in id_set:
            continue
        id_set.add(vid)

        meta = v.get('metadata') or {}
        vtype = (meta.get('memory_type') or meta.get('type') or 'vector').lower()
        content = (v.get('content') or '')
        importance = 0.4
        try:
            importance = float(meta.get('importance') or 0.4)
        except (ValueError, TypeError):
            pass

        color = TYPE_COLORS.get(vtype, TYPE_COLORS['vector'])
        group = vtype if vtype in TYPE_COLORS else 'vector'

        nodes.append({
            'id':         vid,
            'label':      content[:100].replace('\n', ' '),
            'group':      group,
            'color':      color,
            'importance': importance,
            'val':        2 + (importance * 8),
            'tags':       [],
            'created_at': (meta.get('timestamp') or meta.get('created_at') or '')[:10],
        })
        type_index.setdefault(group, []).append(vid)

        # Store embedding for semantic edge computation
        emb = v.get('embedding')
        if emb and isinstance(emb, list) and len(emb) > 10:
            embeddings[vid] = emb

    # ── Build edges ───────────────────────────────────────────────
    links = []
    seen_edges = set()

    def add_edge(src, tgt, etype, strength=0.5, label=''):
        key = tuple(sorted([src, tgt]))
        if key not in seen_edges and src != tgt:
            seen_edges.add(key)
            links.append({
                'source': src, 'target': tgt,
                'type': etype, 'strength': round(strength, 3), 'label': label,
            })

    # 1. SEMANTIC SIMILARITY edges (the core feature)
    #    Compute pairwise cosine similarity for vectors that have embeddings.
    #    Higher similarity → stronger edge → nodes rendered closer.
    emb_ids = list(embeddings.keys())
    SIM_THRESHOLD = 0.55
    MAX_SEMANTIC_EDGES = 300
    sem_edge_count = 0
    for i in range(len(emb_ids)):
        if sem_edge_count >= MAX_SEMANTIC_EDGES:
            break
        for j in range(i + 1, len(emb_ids)):
            if sem_edge_count >= MAX_SEMANTIC_EDGES:
                break
            sim = _cosine_sim(embeddings[emb_ids[i]], embeddings[emb_ids[j]])
            if sim >= SIM_THRESHOLD:
                add_edge(emb_ids[i], emb_ids[j], 'semantic', strength=sim)
                sem_edge_count += 1

    # 2. Tag-based edges
    for tag, mids in tag_index.items():
        if len(mids) > 20:
            continue
        for i in range(len(mids)):
            for j in range(i + 1, len(mids)):
                add_edge(mids[i], mids[j], 'tag', strength=0.6, label=tag)

    # 3. Provenance edges
    for m in memories:
        mid = m.get('id', '')
        prov = m.get('provenance') or ''
        if prov and prov in id_set:
            add_edge(prov, mid, 'provenance', strength=0.8)

    # 4. metadata.related_ids
    for m in memories:
        mid = m.get('id', '')
        meta = m.get('metadata') or {}
        if isinstance(meta, str):
            try:
                import json as _json
                meta = _json.loads(meta)
            except Exception:
                meta = {}
        for rid in (meta.get('related_ids') or []):
            if isinstance(rid, str) and rid in id_set:
                add_edge(mid, rid, 'related', strength=0.7)

    # 5. Type-clustering (light gravity toward type hub)
    for mtype, mids in type_index.items():
        if len(mids) >= 2:
            hub = mids[0]
            for m in mids[1:min(len(mids), 12)]:
                add_edge(hub, m, 'cluster', strength=0.2)

    # Stats for the frontend
    type_counts = {k: len(v) for k, v in type_index.items()}

    return {'nodes': nodes, 'links': links, 'stats': type_counts}


@gitmem_bp.route('/api/agent/<agent_id>/graph')
@login_required
def api_agent_graph(agent_id):
    """Return semantically-aware knowledge graph for force-graph visualization."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"nodes": [], "links": [], "stats": {}}), 200

    # 1. Fetch memories from Supabase
    memories = []
    if _db():
        try:
            res = _db().table('gitmem_memories') \
                .select('id,content,type,importance,tags,provenance,metadata,created_at') \
                .eq('agent_id', agent_id) \
                .order('created_at', desc=True) \
                .limit(200) \
                .execute()
            memories = res.data or []
        except Exception as e:
            print(f"[Graph] Memory fetch error: {e}")

    # 2. Fetch vectors WITH embeddings from ChromaDB (for semantic similarity)
    vectors = []
    try:
        ve = gitmem_app.vector_engine
        if ve and ve.client:
            target = ve.collection
            if ve.is_cloud:
                try:
                    target = ve.client.get_collection(name=agent_id)
                except Exception:
                    pass
            if target:
                results = target.get(
                    where={"agent_id": agent_id} if target == ve.collection else None,
                    limit=150,
                    include=["documents", "metadatas", "embeddings"]
                )
                if results and results.get('ids'):
                    for i, vid in enumerate(results['ids']):
                        vectors.append({
                            'id': vid,
                            'content': (results.get('documents') or [])[i] if results.get('documents') and len(results['documents']) > i else '',
                            'metadata': (results.get('metadatas') or [])[i] if results.get('metadatas') and len(results['metadatas']) > i else {},
                            'embedding': (results.get('embeddings') or [])[i] if results.get('embeddings') and len(results['embeddings']) > i else None,
                        })
    except Exception as e:
        print(f"[Graph] Vector fetch error: {e}")
        # Fallback: try without embeddings
        try:
            vectors = gitmem_app.vector_engine.get_agent_vectors(agent_id, limit=100)
        except Exception:
            pass

    # 3. Fetch chunks from Document Agentic_RAG
    try:
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        import os
        file_db_path = os.getenv("CHROMA_DATABASE_FILE_DATA")
        if file_db_path:
            file_rag = Agentic_RAG(database=file_db_path, enable_cache=False, enable_monitoring=False)
            file_col = file_rag.wrapper.manager.get_collection(agent_id)
            if file_col:
                cdata = file_col.get(limit=100, include=["documents", "metadatas", "embeddings"])
                f_ids = cdata.get("ids", [])
                f_docs = cdata.get("documents", [])
                f_metas = cdata.get("metadatas", [])
                f_embs = cdata.get("embeddings", [])
                
                for i, cid in enumerate(f_ids):
                    meta = f_metas[i] if f_metas and i < len(f_metas) else {}
                    meta['memory_type'] = 'document'
                    vectors.append({
                        'id': cid,
                        'content': f_docs[i] if f_docs and i < len(f_docs) else '',
                        'metadata': meta,
                        'embedding': f_embs[i] if f_embs and i < len(f_embs) else None,
                    })
    except Exception as e:
        print(f"[Graph] Chunk fetch error: {e}")

    graph = _build_graph_data(memories, vectors)
    return jsonify(graph)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Settings & Lifecycle APIs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/agent/<agent_id>/settings', methods=['GET', 'PUT'])
@login_required
def api_agent_settings(agent_id):
    """Get or update agent settings."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403

    if request.method == 'GET':
        agent = _get_agent(agent_id)
        return jsonify({"status": "success", "data": agent})

    # PUT — update settings
    data = request.get_json(silent=True) or {}
    allowed = {'agent_name', 'description', 'status', 'metadata', 'limits', 'permissions'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields"}), 400

    try:
        from backend_examples.python.services.api_agents import ApiAgentsService
        svc = ApiAgentsService()
        updated = svc.update_agent(agent_id=agent_id, user_id=current_user.get_id(), updates=updates)
        return jsonify({"status": "success", "data": updated})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/archive', methods=['POST'])
@login_required
def api_agent_archive(agent_id):
    """Archive (disable) an agent."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    try:
        from backend_examples.python.services.api_agents import ApiAgentsService
        svc = ApiAgentsService()
        svc.disable_agent(agent_id=agent_id, user_id=current_user.get_id())
        return jsonify({"status": "success", "message": "Agent archived"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>', methods=['DELETE'])
@login_required
def api_agent_delete(agent_id):
    """Permanently delete an agent and all its data."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    try:
        from backend_examples.python.services.api_agents import ApiAgentsService
        svc = ApiAgentsService()
        svc.delete_agent(agent_id=agent_id, user_id=current_user.get_id())
        # Also delete memories and commits
        if _db():
            _db().table('gitmem_memories').delete().eq('agent_id', agent_id).execute()
            _db().table('gitmem_commits').delete().eq('agent_id', agent_id).execute()
        return jsonify({"status": "success", "message": "Agent deleted"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Diff API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/diff')
@login_required
def api_diff():
    """Compare two commits and return diff with summary matching frontend expectations."""
    sha_from = request.args.get('from', '')
    sha_to = request.args.get('to', '')
    if not sha_from or not sha_to:
        return jsonify({"error": "Missing from and to params"}), 400
    if not getattr(gitmem_app, 'vcs', None):
        return jsonify({"error": "VCS engine not initialized"}), 503

    try:
        diff = gitmem_app.vcs.diff_engine.diff_commits(sha_from, sha_to)
        stats = gitmem_app.vcs.diff_engine.compute_stats(diff)
        stats_dict = stats.model_dump() if hasattr(stats, 'model_dump') else {"added": 0, "modified": 0, "deleted": 0}
        diff_dict = diff if isinstance(diff, dict) else {"added": [], "modified": [], "deleted": []}
        # Return shape the frontend diff_viewer.html expects
        return jsonify({
            "status": "success",
            "diff": {
                "summary": {"added": stats_dict.get("added", 0), "removed": stats_dict.get("deleted", 0), "modified": stats_dict.get("modified", 0)},
                "added": diff_dict.get("added", []),
                "modified": diff_dict.get("modified", []),
                "removed": diff_dict.get("deleted", []),
            },
            "stats": stats_dict
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VCS OPERATIONS — Branch, Merge, Rollback
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/agent/<agent_id>/branches', methods=['GET'])
@login_required
def api_list_branches(agent_id):
    """List all branches for an agent/repo."""
    db = _db()
    if not db:
        return jsonify([])
    try:
        res = db.table('gitmem_refs').select('*').eq('repo_id', agent_id).eq('ref_type', 'branch').execute()
        return jsonify(res.data or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/branches', methods=['POST'])
@login_required
def api_create_branch(agent_id):
    """Create a new branch from an existing branch or commit hash."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    data = request.get_json(silent=True) or {}
    branch_name = data.get('name', '').strip()
    source = data.get('source', 'main')  # branch name or commit hash
    if not branch_name:
        return jsonify({"error": "Branch name is required"}), 400
    # Sanitize
    branch_name = re.sub(r'[^a-zA-Z0-9._/-]', '', branch_name)
    if not branch_name:
        return jsonify({"error": "Invalid branch name"}), 400
    try:
        result = gitmem_app.vcs.branch(
            repo_id=agent_id,
            branch_name=branch_name,
            target_branch_or_hash=source,
            actor_id=current_user.get_id(),
            workspace_id='default' # API will attempt to auto-resolve if repo missing
        )
        if not result:
            return jsonify({"error": f"Failed to create branch '{branch_name}'. It may already exist or the source branch '{source}' is invalid."}), 400

        return jsonify({"ok": True, "branch": branch_name}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/branches/<branch_name>', methods=['DELETE'])
@login_required
def api_delete_branch(agent_id, branch_name):
    """Delete a branch (cannot delete 'main')."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    if branch_name == 'main':
        return jsonify({"error": "Cannot delete the main branch"}), 400
    try:
        result = gitmem_app.vcs.branch_manager.delete_branch(
            repo_id=agent_id, branch_name=branch_name, actor_id=current_user.get_id()
        )
        return jsonify({"ok": True, "deleted": bool(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/merge', methods=['POST'])
@login_required
def api_merge_branches(agent_id):
    """Merge source branch into target branch."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    data = request.get_json(silent=True) or {}
    target = data.get('target', 'main')
    source = data.get('source', '')
    policy = data.get('policy', 'last_write_wins')
    if not source:
        return jsonify({"error": "source branch is required"}), 400
    try:
        from gitmem.core.models import MergePolicy
        policy_enum = MergePolicy(policy)
        result = gitmem_app.vcs.merge(
            repo_id=agent_id,
            target_branch=target,
            source_branch=source,
            actor_id=current_user.get_id(),
            workspace_id='default',
            policy=policy_enum
        )
        if result.get('status') == 'error':
            return jsonify({"error": result.get('error', 'Merge failed')}), 400
        return jsonify({"ok": True, "commit_hash": result.get('commit_hash', '')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/rollback', methods=['POST'])
@login_required
def api_rollback(agent_id):
    """Rollback branch to a specific commit."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    data = request.get_json(silent=True) or {}
    branch = data.get('branch', 'main')
    target_hash = data.get('hash', '')
    if not target_hash:
        return jsonify({"error": "target hash is required"}), 400
    try:
        success = gitmem_app.vcs.rollback(
            repo_id=agent_id,
            branch_name=branch,
            target_hash=target_hash,
            actor_id=current_user.get_id()
        )
        if not success:
            return jsonify({"error": "Rollback failed"}), 400
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Checkpoints API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/checkpoints/<agent_id>/create', methods=['POST'])
@login_required
def api_checkpoint_create(agent_id):
    """Create a memory checkpoint/snapshot."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403

    data = request.get_json(silent=True) or {}
    name = data.get('name', 'Unnamed checkpoint')
    checkpoint_type = data.get('type', 'snapshot')

    try:
        import uuid
        checkpoint_id = str(uuid.uuid4())
        # Count memories by type for snapshot
        memory_counts = {}
        for mtype in ['episodic', 'semantic', 'procedural', 'state']:
            memory_counts[mtype] = _count_table_where('gitmem_memories', {'agent_id': agent_id, 'type': mtype})

        row = {
            'id': checkpoint_id,
            'agent_id': agent_id,
            'checkpoint_type': checkpoint_type,
            'name': name,
            'memory_counts': memory_counts,
            'metadata': {},
        }
        db = _db()
        if not db:
            return jsonify({"error": "Database unavailable"}), 503
        db.table('gitmem_checkpoints').insert(row).execute()
        return jsonify({"status": "success", "id": checkpoint_id})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Logs API (JSON endpoint for activity_logs.html)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/logs/<agent_id>')
@login_required
def api_logs(agent_id):
    """Get activity logs for an agent as JSON."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403

    limit = request.args.get('limit', 100, type=int)
    log_type = request.args.get('type')

    db = _db()
    if not db:
        return jsonify({"status": "success", "data": []})
    try:
        q = db.table('gitmem_activity_logs').select('*').eq('agent_id', agent_id)
        if log_type:
            q = q.eq('log_type', log_type)
        res = q.order('created_at', desc=True).limit(limit).execute()
        return jsonify({"status": "success", "data": res.data or []})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Star API (for github_shell.html)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/documents')
@login_required
def agent_documents(agent_id):
    """Document management page."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)
    documents = []
    if _db():
        try:
            res = _db().table('gitmem_documents').select('*') \
                .eq('agent_id', agent_id).order('created_at', desc=True).limit(50).execute()
            documents = res.data or []
        except Exception:
            pass
    # Branches
    current_branch = request.args.get('branch', 'main')
    branches = []
    try:
        branches_raw = gitmem_app.vcs.branch_manager.list_branches(agent_id)
        branches = [b.get('ref_name') for b in branches_raw if b.get('ref_name')]
        if not branches or 'main' not in branches:
            branches.insert(0, 'main')
    except Exception:
        branches = ['main']

    return render_template('documents.html', agent=agent, documents=documents, branches=branches, current_branch=current_branch, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/memories')
@login_required
def agent_memories(agent_id):
    """Memory listing page."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)
    memories = []
    if _db():
        try:
            res = _db().table('gitmem_memories').select('*') \
                .eq('agent_id', agent_id).order('created_at', desc=True).limit(100).execute()
            memories = res.data or []
        except Exception:
            pass
    # Branches
    current_branch = request.args.get('branch', 'main')
    branches = []
    try:
        branches_raw = gitmem_app.vcs.branch_manager.list_branches(agent_id)
        branches = [b.get('ref_name') for b in branches_raw if b.get('ref_name')]
        if not branches or 'main' not in branches:
            branches.insert(0, 'main')
    except Exception:
        branches = ['main']

    return render_template('memories.html', agent=agent, memories=memories, branches=branches, current_branch=current_branch, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/sources')
@login_required
def agent_sources(agent_id):
    """Data sources management page."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)
    # Branches for shell
    current_branch = request.args.get('branch', 'main')
    branches = []
    try:
        branches_raw = gitmem_app.vcs.branch_manager.list_branches(agent_id)
        branches = [b.get('ref_name') for b in branches_raw if b.get('ref_name')]
        if not branches or 'main' not in branches:
            branches.insert(0, 'main')
    except Exception:
        branches = ['main']

    return render_template('sources.html', agent=agent, branches=branches, current_branch=current_branch, sources=get_sources_status())


@gitmem_bp.route('/api/star', methods=['POST'])
@login_required
def api_star():
    """Toggle star on an agent repo (stored in user metadata)."""
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id', '')
    # Simple acknowledgment — star state can be stored in agent metadata
    return jsonify({"status": "starred", "count": 1})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WORKSPACE & TEAM MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/workspaces', methods=['GET'])
@login_required
def api_list_workspaces():
    """List all workspaces the current user belongs to."""
    db = _db()
    if not db:
        return jsonify([])
    try:
        # Get membership records
        mem_res = db.table('gitmem_workspace_members').select('workspace_id, role').eq('user_id', current_user.get_id()).execute()
        memberships = mem_res.data or []
        if not memberships:
            return jsonify([])
        ws_ids = [m['workspace_id'] for m in memberships]
        ws_res = db.table('gitmem_workspaces').select('*').in_('workspace_id', ws_ids).execute()
        workspaces = ws_res.data or []
        # Attach user's role to each workspace
        role_map = {m['workspace_id']: m['role'] for m in memberships}
        for ws in workspaces:
            ws['user_role'] = role_map.get(ws['workspace_id'], 'viewer')
        return jsonify(workspaces)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/workspaces', methods=['POST'])
@login_required
def api_create_workspace():
    """Create a new workspace. Current user becomes owner."""
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    slug = data.get('slug', '').strip()
    if not name or not slug:
        return jsonify({'error': 'name and slug are required'}), 400
    # Sanitize slug
    slug = re.sub(r'[^a-z0-9-]', '', slug.lower())
    if not slug:
        return jsonify({'error': 'invalid slug'}), 400
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        import uuid
        from datetime import datetime
        ws_id = str(uuid.uuid4())
        user_id = current_user.get_id()
        # Create workspace
        db.table('gitmem_workspaces').insert({
            'workspace_id': ws_id,
            'name': name,
            'slug': slug,
            'owner_id': user_id,
            'plan': 'free',
            'settings': {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }).execute()
        # Add owner as member
        db.table('gitmem_workspace_members').insert({
            'workspace_id': ws_id,
            'user_id': user_id,
            'role': 'owner',
            'invited_by': user_id,
            'joined_at': datetime.utcnow().isoformat(),
        }).execute()
        return jsonify({'ok': True, 'workspace_id': ws_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/workspaces/<ws_id>/members', methods=['GET'])
@login_required
def api_list_members(ws_id):
    """List all members of a workspace."""
    db = _db()
    if not db:
        return jsonify([])
    try:
        res = db.table('gitmem_workspace_members').select('*').eq('workspace_id', ws_id).execute()
        members = res.data or []
        # Enrich with user profile info
        user_ids = [m['user_id'] for m in members]
        if user_ids:
            profiles_res = db.table('profiles').select('id, email, full_name, avatar_url').in_('id', user_ids).execute()
            profile_map = {p['id']: p for p in (profiles_res.data or [])}
            for m in members:
                profile = profile_map.get(m['user_id'], {})
                m['email'] = profile.get('email', '')
                m['full_name'] = profile.get('full_name', '')
                m['avatar_url'] = profile.get('avatar_url', '')
        return jsonify(members)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/workspaces/<ws_id>/members', methods=['POST'])
@login_required
def api_invite_member(ws_id):
    """Invite a user to a workspace by email."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    role = data.get('role', 'member')
    if not email:
        return jsonify({'error': 'email is required'}), 400
    if role not in ('admin', 'member', 'viewer'):
        return jsonify({'error': 'role must be admin, member, or viewer'}), 400
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        from datetime import datetime
        # Find user by email
        user_res = db.table('profiles').select('id, email, full_name').eq('email', email).limit(1).execute()
        if not user_res.data:
            return jsonify({'error': f'No user found with email {email}'}), 404
        target_user = user_res.data[0]
        # Check not already a member
        existing = db.table('gitmem_workspace_members').select('user_id').eq('workspace_id', ws_id).eq('user_id', target_user['id']).execute()
        if existing.data:
            return jsonify({'error': 'User is already a member of this workspace'}), 409
        # Add member
        db.table('gitmem_workspace_members').insert({
            'workspace_id': ws_id,
            'user_id': target_user['id'],
            'role': role,
            'invited_by': current_user.get_id(),
            'joined_at': datetime.utcnow().isoformat(),
        }).execute()
        return jsonify({'ok': True, 'user_id': target_user['id'], 'email': email, 'role': role}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/workspaces/<ws_id>/members/<user_id>', methods=['PUT'])
@login_required
def api_update_member_role(ws_id, user_id):
    """Update a workspace member's role."""
    data = request.get_json(silent=True) or {}
    role = data.get('role', '')
    if role not in ('admin', 'member', 'viewer'):
        return jsonify({'error': 'role must be admin, member, or viewer'}), 400
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        db.table('gitmem_workspace_members').update({'role': role}).eq('workspace_id', ws_id).eq('user_id', user_id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/workspaces/<ws_id>/members/<user_id>', methods=['DELETE'])
@login_required
def api_remove_member(ws_id, user_id):
    """Remove a member from a workspace."""
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        db.table('gitmem_workspace_members').delete().eq('workspace_id', ws_id).eq('user_id', user_id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REPOSITORY COLLABORATORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/agent/<agent_id>/collaborators', methods=['GET'])
@login_required
def api_list_collaborators(agent_id):
    """List collaborators for a repository (agent)."""
    db = _db()
    if not db:
        return jsonify([])
    try:
        res = db.table('gitmem_collaborators').select('*').eq('repo_id', agent_id).execute()
        collabs = res.data or []
        # Enrich with profile info
        user_ids = [c['user_id'] for c in collabs]
        if user_ids:
            profiles_res = db.table('profiles').select('id, email, full_name, avatar_url').in_('id', user_ids).execute()
            profile_map = {p['id']: p for p in (profiles_res.data or [])}
            for c in collabs:
                profile = profile_map.get(c['user_id'], {})
                c['email'] = profile.get('email', '')
                c['full_name'] = profile.get('full_name', '')
                c['avatar_url'] = profile.get('avatar_url', '')
        return jsonify(collabs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/collaborators', methods=['POST'])
@login_required
def api_add_collaborator(agent_id):
    """Add a collaborator to a repository by email."""
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    role = data.get('role', 'reader')
    if not email:
        return jsonify({'error': 'email is required'}), 400
    if role not in ('admin', 'writer', 'reader'):
        return jsonify({'error': 'role must be admin, writer, or reader'}), 400
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        from datetime import datetime
        # Find user
        user_res = db.table('profiles').select('id, email, full_name').eq('email', email).limit(1).execute()
        if not user_res.data:
            return jsonify({'error': f'No user found with email {email}'}), 404
        target_user = user_res.data[0]
        # Check not already added
        existing = db.table('gitmem_collaborators').select('user_id').eq('repo_id', agent_id).eq('user_id', target_user['id']).execute()
        if existing.data:
            return jsonify({'error': 'User is already a collaborator on this repo'}), 409
        db.table('gitmem_collaborators').insert({
            'repo_id': agent_id,
            'user_id': target_user['id'],
            'role': role,
            'added_by': current_user.get_id(),
            'accepted': True,
            'created_at': datetime.utcnow().isoformat(),
        }).execute()
        return jsonify({'ok': True, 'user_id': target_user['id'], 'email': email, 'role': role}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/collaborators/<user_id>', methods=['PUT'])
@login_required
def api_update_collaborator_role(agent_id, user_id):
    """Update a collaborator's role on a repository."""
    data = request.get_json(silent=True) or {}
    role = data.get('role', '')
    if role not in ('admin', 'writer', 'reader'):
        return jsonify({'error': 'role must be admin, writer, or reader'}), 400
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        db.table('gitmem_collaborators').update({'role': role}).eq('repo_id', agent_id).eq('user_id', user_id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@gitmem_bp.route('/api/agent/<agent_id>/collaborators/<user_id>', methods=['DELETE'])
@login_required
def api_remove_collaborator(agent_id, user_id):
    """Remove a collaborator from a repository."""
    db = _db()
    if not db:
        return jsonify({'error': 'database unavailable'}), 503
    try:
        db.table('gitmem_collaborators').delete().eq('repo_id', agent_id).eq('user_id', user_id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USER SEARCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/api/users/search', methods=['GET'])
@login_required
def api_search_users():
    """Search users by email or name for invite flows."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    db = _db()
    if not db:
        return jsonify([])
    try:
        res = db.table('profiles').select('id, email, full_name, avatar_url').or_(f"email.ilike.%{q}%,full_name.ilike.%{q}%").limit(8).execute()
        return jsonify(res.data or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
