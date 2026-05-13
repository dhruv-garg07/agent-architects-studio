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

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
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


def _get_agent(agent_id, user_id=None):
    """Fetch agent from api_agents. Returns dict or None."""
    if not _db():
        return None
    try:
        q = _db().table('api_agents').select('*').eq('agent_id', agent_id)
        if user_id:
            q = q.eq('user_id', user_id)
        res = q.execute()
        return res.data[0] if res.data else None
    except Exception:
        return None


def _agent_context(agent_id, agent_raw):
    """Build a consistent agent context dict for templates (used by github_shell)."""
    return {
        'id': agent_id,
        'name': (agent_raw or {}).get('agent_name') or agent_id,
        'slug': (agent_raw or {}).get('agent_slug') or agent_id[:8],
        'description': (agent_raw or {}).get('description') or '',
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
    Returns {context, documents, vectors, checkpoints, logs} with counts.
    """
    # Context Store → memories grouped by type
    context = {}
    for mtype in ['episodic', 'semantic', 'procedural', 'state']:
        context[mtype] = {'count': _count_table_where('gitmem_memories', {'agent_id': agent_id, 'type': mtype})}

    # Documents → grouped by folder
    documents = {}
    for folder in ['uploads', 'attachments', 'references']:
        documents[folder] = {'count': _count_table_where('gitmem_documents', {'agent_id': agent_id, 'folder': folder})}

    # Vectors → from ChromaDB
    vectors = {}
    try:
        raw = gitmem_app.vector_engine.get_agent_vectors(agent_id, limit=200)
        bins = gitmem_app.vector_engine.categorize_vectors(raw)
        for k in ['episodic', 'semantic', 'procedural', 'working']:
            vectors[k] = {'count': len(bins.get(k, []))}
    except Exception:
        vectors = {'all': {'count': 0}}

    # Checkpoints → grouped by type
    checkpoints = {}
    for ctype in ['snapshot', 'session', 'recovery', 'auto']:
        checkpoints[ctype] = {'count': _count_table_where('gitmem_checkpoints', {'agent_id': agent_id, 'checkpoint_type': ctype})}

    # Activity Logs → grouped by log_type
    logs = {}
    for ltype in ['access', 'mutation', 'error', 'system']:
        logs[ltype] = {'count': _count_table_where('gitmem_activity_logs', {'agent_id': agent_id, 'log_type': ltype})}

    return {
        'context': context,
        'documents': documents,
        'vectors': vectors,
        'checkpoints': checkpoints,
        'logs': logs,
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
        for name in ['context', 'docs', 'vectors', 'checkpoints', 'logs']:
            items.append({'name': name, 'type': 'directory', 'path': name, 'last_modified': ''})
        return items

    root = parts[0]

    # Level 1: show subfolders
    if depth == 1:
        if root == 'context':
            for t in ['episodic', 'semantic', 'procedural', 'state']:
                items.append({'name': t, 'type': 'directory', 'path': f'context/{t}', 'last_modified': ''})
        elif root in ('docs', 'documents'):
            for f in ['uploads', 'attachments', 'references']:
                items.append({'name': f, 'type': 'directory', 'path': f'docs/{f}', 'last_modified': ''})
        elif root == 'vectors':
            for t in ['episodic', 'semantic', 'procedural', 'working']:
                items.append({'name': t, 'type': 'directory', 'path': f'vectors/{t}', 'last_modified': ''})
        elif root == 'checkpoints':
            for t in ['snapshot', 'session', 'recovery', 'auto']:
                items.append({'name': t, 'type': 'directory', 'path': f'checkpoints/{t}', 'last_modified': ''})
        elif root == 'logs':
            for t in ['access', 'mutation', 'error', 'system']:
                items.append({'name': t, 'type': 'directory', 'path': f'logs/{t}', 'last_modified': ''})
        return items

    # Level 2: show actual data as files
    subfolder = parts[1] if len(parts) > 1 else ''
    if root == 'context' and subfolder and _db():
        try:
            res = _db().table('gitmem_memories').select('id,content,created_at') \
                .eq('agent_id', agent_id).eq('type', subfolder) \
                .order('created_at', desc=True).limit(50).execute()
            for row in (res.data or []):
                label = (row.get('content', '') or '')[:60].replace('\n', ' ')
                items.append({
                    'name': f"{row['id'][:8]} — {label}",
                    'type': 'file',
                    'path': f"context/{subfolder}/{row['id']}",
                    'last_modified': row.get('created_at', ''),
                })
        except Exception:
            pass

    elif root in ('docs', 'documents') and subfolder and _db():
        try:
            res = _db().table('gitmem_documents').select('id,filename,created_at') \
                .eq('agent_id', agent_id).eq('folder', subfolder) \
                .order('created_at', desc=True).limit(50).execute()
            for row in (res.data or []):
                items.append({
                    'name': row.get('filename', row['id'][:8]),
                    'type': 'file',
                    'path': f"docs/{subfolder}/{row['id']}",
                    'last_modified': row.get('created_at', ''),
                })
        except Exception:
            pass

    elif root == 'vectors' and subfolder:
        try:
            raw = gitmem_app.vector_engine.get_agent_vectors(agent_id, limit=100)
            bins = gitmem_app.vector_engine.categorize_vectors(raw)
            for v in bins.get(subfolder, []):
                label = (v.get('content', '') or '')[:60].replace('\n', ' ')
                items.append({
                    'name': f"{v['id'][:8]} — {label}",
                    'type': 'file',
                    'path': f"vectors/{subfolder}/{v['id']}",
                    'last_modified': v.get('created_at', ''),
                })
        except Exception:
            pass

    elif root == 'checkpoints' and subfolder and _db():
        try:
            res = _db().table('gitmem_checkpoints').select('id,name,created_at') \
                .eq('agent_id', agent_id).eq('checkpoint_type', subfolder) \
                .order('created_at', desc=True).limit(50).execute()
            for row in (res.data or []):
                items.append({
                    'name': row.get('name', row['id'][:8]),
                    'type': 'file',
                    'path': f"checkpoints/{subfolder}/{row['id']}",
                    'last_modified': row.get('created_at', ''),
                })
        except Exception:
            pass

    elif root == 'logs' and subfolder and _db():
        try:
            res = _db().table('gitmem_activity_logs').select('id,action,resource_type,created_at') \
                .eq('agent_id', agent_id).eq('log_type', subfolder) \
                .order('created_at', desc=True).limit(50).execute()
            for row in (res.data or []):
                items.append({
                    'name': f"{row.get('action', '?')} {row.get('resource_type', '')}",
                    'type': 'file',
                    'path': f"logs/{subfolder}/{row['id']}",
                    'last_modified': row.get('created_at', ''),
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
    """Agent repository list — one card per agent."""
    agents_raw = []
    if _db():
        try:
            res = _db().table('api_agents').select('*') \
                .eq('user_id', current_user.get_id()) \
                .order('created_at', desc=True).execute()
            agents_raw = res.data or []
        except Exception as e:
            print(f"[GitMem] landing fetch error: {e}")

    repos = []
    total_memories, total_commits = 0, 0
    for agent in agents_raw:
        aid = agent.get('agent_id')
        mem_count = _count_table('gitmem_memories', 'agent_id', aid)
        commit_count = _count_table('gitmem_commits', 'agent_id', aid)
        vec_count = 0
        try:
            vec_count = gitmem_app.vector_engine.get_agent_stats(aid).get('embeddings', 0)
        except Exception:
            pass

        agent_meta = agent.get('metadata') or {}
        if isinstance(agent_meta, str):
            try:
                import json as _json
                agent_meta = _json.loads(agent_meta)
            except Exception:
                agent_meta = {}
        repos.append({
            'repo_id':       aid,
            'name':          agent.get('agent_name') or agent.get('agent_slug') or aid,
            'description':   agent.get('description') or '',
            'visibility':    'private',
            'default_branch': 'main',
            'created_at':    agent.get('created_at', ''),
            'updated_at':    agent.get('updated_at', ''),
            'status':        agent.get('status', 'active'),
            'memory_count':  mem_count,
            'commit_count':  commit_count,
            'vector_count':  vec_count,
            'workspace_id':  agent_meta.get('workspace_id', ''),
        })
        total_memories += mem_count
        total_commits += commit_count

    stats = {
        'active_workspaces': 1,
        'total_repositories': len(repos),
        'total_memories': total_memories,
        'total_commits': total_commits,
    }

    return render_template('landing.html', repos=repos, workspaces=[], stats=stats, sources=get_sources_status())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Dashboard — File System View (PRIMARY UI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>')
@login_required
def agent_dashboard(agent_id):
    """
    Main agent view — file-system style with folder structure,
    recent memories, activity feed, index stats.
    """
    if not _db():
        flash("Database disconnected", "error")
        return redirect(url_for('gitmem.landing'))

    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        flash("Repository not found or access denied.", "error")
        return redirect(url_for('gitmem.landing'))

    # Build agent object for template
    agent = {
        'id':          agent_id,
        'name':        agent_raw.get('agent_name') or agent_raw.get('agent_slug') or agent_id,
        'slug':        agent_raw.get('agent_slug', agent_id),
        'description': agent_raw.get('description', ''),
        'status':      agent_raw.get('status', 'active'),
    }

    # Folder structure
    folder_structure = _build_folder_structure(agent_id)

    # Recent memories (latest 5)
    recent_context = []
    try:
        res = _db().table('gitmem_memories').select('*') \
            .eq('agent_id', agent_id) \
            .order('created_at', desc=True).limit(5).execute()
        recent_context = res.data or []
    except Exception:
        pass

    # Activity Feed (latest 6)
    activity_feed = []
    try:
        res = _db().table('gitmem_activity_logs').select('*') \
            .eq('agent_id', agent_id) \
            .order('created_at', desc=True).limit(6).execute()
        for row in (res.data or []):
            activity_feed.append({
                'content': f"{row.get('action', '')} {row.get('resource_type', '')}",
                'timestamp': (row.get('created_at', '') or '')[:16],
                'icon': 'activity',
            })
    except Exception:
        pass

    # Index stats from vector engine
    index_stats = {'embeddings': 0, 'latency': '—', 'freshness': 'N/A'}
    try:
        index_stats = gitmem_app.vector_engine.get_agent_stats(agent_id)
    except Exception:
        pass

    # Latest commit
    latest_commit = None
    try:
        res = _db().table('gitmem_commits').select('*') \
            .eq('agent_id', agent_id) \
            .order('timestamp', desc=True).limit(1).execute()
        if res.data:
            latest_commit = res.data[0]
    except Exception:
        pass

    # Context sources count (sum of all folder items)
    context_sources = []
    for section in folder_structure.values():
        for sub in section.values():
            if sub.get('count', 0) > 0:
                context_sources.append(sub)

    memory_count = _count_table('gitmem_memories', 'agent_id', agent_id)
    commit_count = _count_table('gitmem_commits', 'agent_id', agent_id)

    return render_template(
        'agent_dashboard.html',
        agent=agent,
        folder_structure=folder_structure,
        recent_context=recent_context,
        activity_feed=activity_feed,
        index_stats=index_stats,
        latest_commit=latest_commit,
        context_sources=context_sources,
        memory_count=memory_count,
        commit_count=commit_count,
        sources=get_sources_status(),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# File System Browser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/fs/')
@gitmem_bp.route('/agent/<agent_id>/fs/<path:virtual_path>')
@login_required
def agent_fs_view(agent_id, virtual_path=''):
    """Virtual filesystem browser."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        flash("Repository not found.", "error")
        return redirect(url_for('gitmem.landing'))

    agent = {
        'id': agent_id,
        'name': agent_raw.get('agent_name') or agent_id,
        'slug': agent_raw.get('agent_slug', agent_id),
    }

    items = _build_fs_items(agent_id, virtual_path)

    return render_template(
        'file_browser.html',
        agent=agent,
        current_path=virtual_path,
        items=items,
        sources=get_sources_status(),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# File View (single memory/document)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/file/<path:virtual_path>')
@login_required
def agent_file_view(agent_id, virtual_path=''):
    """View a single memory item or document."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        flash("Repository not found.", "error")
        return redirect(url_for('gitmem.landing'))

    agent = {
        'id': agent_id,
        'name': agent_raw.get('agent_name') or agent_id,
        'slug': agent_raw.get('agent_slug', agent_id),
    }

    # Parse path to figure out source: context/{type}/{id}, docs/{folder}/{id}, vectors/{type}/{id}
    parts = [p for p in virtual_path.strip('/').split('/') if p]
    file_content = 'Item not found'
    metadata = {}

    if len(parts) >= 3 and _db():
        root, subfolder, item_id = parts[0], parts[1], parts[2]
        try:
            if root == 'context':
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
            elif root in ('docs', 'documents'):
                res = _db().table('gitmem_documents').select('*').eq('id', item_id).execute()
                if res.data:
                    row = res.data[0]
                    file_content = row.get('content', '')
                    metadata = row.get('metadata', {}) if isinstance(row.get('metadata'), dict) else {}
                    metadata.update({
                        'filename': row.get('filename'),
                        'folder': row.get('folder'),
                        'created_at': row.get('created_at')
                    })
            elif root == 'vectors':
                v = gitmem_app.vector_engine.get_vector(item_id, agent_id)
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

    return render_template(
        'file_view.html',
        agent=agent,
        path=virtual_path,
        content=file_content,
        metadata=metadata,
        sources=get_sources_status(),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Commit Log
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/commits')
@login_required
def agent_commits(agent_id):
    """Commit history page."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        flash("Repository not found.", "error")
        return redirect(url_for('gitmem.landing'))

    agent = {
        'id': agent_id,
        'name': agent_raw.get('agent_name') or agent_id,
        'slug': agent_raw.get('agent_slug', agent_id),
    }

    current_branch = request.args.get('branch', 'main')

    # Branches
    branches = []
    try:
        branches = gitmem_app.vcs.branch_manager.list_branches(agent_id)
    except Exception:
        pass

    branch_names = [b.get('ref_name', 'main') for b in branches]

    # Get commits — filter by branch if we have ref data
    commits = []
    try:
        db = _db()
        if db:
            query = db.table('gitmem_commits').select('*').eq('agent_id', agent_id)
            query = query.order('timestamp', desc=True).limit(100)
            res = query.execute()
            commits = res.data or []
    except Exception:
        pass

    memory_count = _count_table('gitmem_memories', 'agent_id', agent_id)

    return render_template(
        'commit_log.html',
        agent=agent,
        commits=commits,
        commit_count=len(commits),
        memory_count=memory_count,
        branches=branch_names,
        current_branch=current_branch,
        sources=get_sources_status(),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Diff Viewer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/diffs')
@login_required
def agent_diffs(agent_id):
    """Diff viewer between commits."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))

    agent = _agent_context(agent_id, agent_raw)

    commits = []
    try:
        db = _db()
        if db:
            res = db.table('gitmem_commits').select('hash,message,timestamp,author_id') \
                .eq('agent_id', agent_id) \
                .order('timestamp', desc=True).limit(50).execute()
            for c in (res.data or []):
                commits.append({'sha': c['hash'], 'message': c.get('message', ''), 'timestamp': c.get('timestamp', '')})
    except Exception:
        pass

    import json
    commits_json = json.dumps(commits)
    return render_template('diff_viewer.html', agent=agent, commits=commits, commits_json=commits_json, sources=get_sources_status())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Placeholder pages (Issues, Pulls, Settings, Wiki, etc.)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/pulls')
@login_required
def pulls(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    return render_template('pulls.html', agent=agent, pulls=[], sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/issues')
@login_required
def issues(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    return render_template('issues.html', agent=agent, issues=[], sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/settings')
@login_required
def settings(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)
    # Get workspace_id for team management (default workspace if not set)
    workspace_id = agent_raw.get('workspace_id', 'default')
    return render_template('settings.html', agent=agent, workspace_id=workspace_id, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/wiki')
@login_required
def wiki(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = _agent_context(agent_id, agent_raw)
    return render_template('wiki.html', agent=agent, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/checkpoints')
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


@gitmem_bp.route('/agent/<agent_id>/logs')
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
        flash("Agent ID is required.", "error")
        return redirect(url_for('gitmem.create_agent_form'))

    if not _db():
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
        # Create default branch
        try:
            gitmem_app.vcs.branch_manager.create_branch(agent_id, 'main', 'HEAD', current_user.get_id())
        except Exception:
            pass

        flash(f"Repository '{agent_name}' created.", "success")
        return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))
    except Exception as e:
        flash(f"Failed to create repository: {e}", "error")
        return redirect(url_for('gitmem.create_agent_form'))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Endpoints
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
            gitmem_app.vector_engine.delete_memory(memory_id)
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
                gitmem_app.vector_engine.delete_memory(memory_id)
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
            actor_id=current_user.get_id()
        )
        return jsonify({"ok": True, "branch": branch_name, "created": bool(result)}), 201
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
    """Rollback a branch to a specific commit hash."""
    if not _get_agent(agent_id, user_id=current_user.get_id()):
        return jsonify({"error": "Access denied"}), 403
    data = request.get_json(silent=True) or {}
    branch = data.get('branch', 'main')
    target_hash = data.get('target_hash', '')
    if not target_hash:
        return jsonify({"error": "target_hash is required"}), 400
    try:
        result = gitmem_app.vcs.rollback(
            repo_id=agent_id,
            branch_name=branch,
            target_hash=target_hash,
            actor_id=current_user.get_id()
        )
        return jsonify({"ok": True, "rolled_back": bool(result), "branch": branch, "target": target_hash})
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
    return render_template('documents.html', agent=agent, documents=documents, sources=get_sources_status())


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
    return render_template('memories.html', agent=agent, memories=memories, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/sources')
@login_required
def agent_sources(agent_id):
    """Data sources management page."""
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = _agent_context(agent_id, agent_raw)
    return render_template('sources.html', agent=agent, sources=get_sources_status())


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
