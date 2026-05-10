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
    content = {'raw': 'Item not found', 'metadata': {}}

    if len(parts) >= 3 and _db():
        root, subfolder, item_id = parts[0], parts[1], parts[2]
        try:
            if root == 'context':
                res = _db().table('gitmem_memories').select('*').eq('id', item_id).execute()
                if res.data:
                    content = res.data[0]
            elif root in ('docs', 'documents'):
                res = _db().table('gitmem_documents').select('*').eq('id', item_id).execute()
                if res.data:
                    content = res.data[0]
            elif root == 'vectors':
                v = gitmem_app.vector_engine.get_vector(item_id, agent_id)
                if v:
                    content = v
            elif root == 'checkpoints':
                res = _db().table('gitmem_checkpoints').select('*').eq('id', item_id).execute()
                if res.data:
                    content = res.data[0]
            elif root == 'logs':
                res = _db().table('gitmem_activity_logs').select('*').eq('id', item_id).execute()
                if res.data:
                    content = res.data[0]
        except Exception:
            pass

    return render_template(
        'file_view.html',
        agent=agent,
        path=virtual_path,
        content=content,
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

    commits = []
    try:
        res = _db().table('gitmem_commits').select('*') \
            .eq('agent_id', agent_id) \
            .order('timestamp', desc=True).limit(100).execute()
        commits = res.data or []
    except Exception:
        pass

    # Branches
    branches = []
    try:
        branches = gitmem_app.vcs.branch_manager.list_branches(agent_id)
    except Exception:
        pass

    memory_count = _count_table('gitmem_memories', 'agent_id', agent_id)

    return render_template(
        'commit_log.html',
        agent=agent,
        commits=commits,
        commit_count=len(commits),
        memory_count=memory_count,
        branches=[b.get('ref_name', 'main') for b in branches],
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

    agent = {'id': agent_id, 'name': agent_raw.get('agent_name') or agent_id}

    commits = []
    try:
        res = _db().table('gitmem_commits').select('hash,message,timestamp,author_id') \
            .eq('agent_id', agent_id) \
            .order('timestamp', desc=True).limit(50).execute()
        for c in (res.data or []):
            commits.append({'sha': c['hash'], 'message': c.get('message', ''), 'timestamp': c.get('timestamp', '')})
    except Exception:
        pass

    return render_template('diff_viewer.html', agent=agent, commits=commits, sources=get_sources_status())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Placeholder pages (Issues, Pulls, Settings, Wiki, etc.)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@gitmem_bp.route('/agent/<agent_id>/pulls')
@login_required
def pulls(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = {'id': agent_id, 'name': (agent_raw or {}).get('agent_name', agent_id)}
    return render_template('pulls.html', agent=agent, pulls=[], sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/issues')
@login_required
def issues(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = {'id': agent_id, 'name': (agent_raw or {}).get('agent_name', agent_id)}
    return render_template('issues.html', agent=agent, issues=[], sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/settings')
@login_required
def settings(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    if not agent_raw:
        return redirect(url_for('gitmem.landing'))
    agent = {'id': agent_id, 'name': agent_raw.get('agent_name', agent_id)}
    return render_template('settings.html', agent=agent, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/wiki')
@login_required
def wiki(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = {'id': agent_id, 'name': (agent_raw or {}).get('agent_name', agent_id)}
    return render_template('wiki.html', agent=agent, sources=get_sources_status())


@gitmem_bp.route('/agent/<agent_id>/checkpoints')
@login_required
def agent_checkpoints(agent_id):
    agent_raw = _get_agent(agent_id, user_id=current_user.get_id())
    agent = {'id': agent_id, 'name': (agent_raw or {}).get('agent_name', agent_id)}
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
    agent = {'id': agent_id, 'name': (agent_raw or {}).get('agent_name', agent_id)}
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
    return render_template('create_agent.html', workspaces=[], sources=get_sources_status())


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
            metadata={"capabilities": [], "status": "active"},
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
        _db().table('gitmem_memories').insert(mem.model_dump(mode='json', exclude={'embedding'})).execute()

        # Also index in vector store
        gitmem_app.vector_engine.add_memory(mem)

        return jsonify({"status": "success", "id": mem.id})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/memory/<memory_id>', methods=['DELETE'])
@login_required
def api_delete_memory(memory_id):
    """Delete a memory."""
    try:
        res = _db().table('gitmem_memories').select('agent_id').eq('id', memory_id).execute()
        if not res.data:
            return jsonify({"error": "Not found"}), 404
        agent_id = res.data[0]['agent_id']
        if not _get_agent(agent_id, user_id=current_user.get_id()):
            return jsonify({"error": "Access denied"}), 403

        _db().table('gitmem_memories').delete().eq('id', memory_id).execute()
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
