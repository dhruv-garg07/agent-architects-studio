"""
GitMem Routes — V2 with V1 backward compatibility

Data Model:
  - Agents  →  api_agents table  (agent_id, user_id, agent_name, agent_slug, ...)
  - Memories → gitmem_memories  (agent_id FK, content, type, importance, ...)
  - Commits  → gitmem_commits   (agent_id FK, hash, message, ...)
  - Refs     → gitmem_refs      (repo_id = agent_id, ref_name, target_hash, ...)

One agent == one repository. agent_id IS the repo_id throughout.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
import re
import os

from gitmem.core.app import gitmem_app

gitmem_bp = Blueprint(
    'gitmem', __name__,
    url_prefix='/gitmem',
    template_folder='../../templates/gitmem'
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _db():
    """Return Supabase client or None."""
    return gitmem_app.supabase_client


def _get_agent(agent_id: str, user_id: str = None):
    """Fetch one agent record from api_agents. Returns dict or None."""
    if not _db():
        return None
    try:
        q = _db().table('api_agents').select('*').eq('agent_id', agent_id)
        if user_id:
            q = q.eq('user_id', user_id)
        res = q.execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[GitMem] _get_agent error: {e}")
        return None


def _get_memory_count(agent_id: str) -> int:
    if not _db():
        return 0
    try:
        res = _db().table('gitmem_memories').select('id', count='exact') \
            .eq('agent_id', agent_id).limit(1).execute()
        return res.count or 0
    except Exception:
        return 0


def _get_commit_count(agent_id: str) -> int:
    if not _db():
        return 0
    try:
        res = _db().table('gitmem_commits').select('hash', count='exact') \
            .eq('agent_id', agent_id).limit(1).execute()
        return res.count or 0
    except Exception:
        return 0


def _agent_to_repo(agent: dict) -> dict:
    """Normalise api_agents row into the shape repo_dashboard.html expects."""
    return {
        'repo_id':        agent.get('agent_id'),
        'name':           agent.get('agent_name') or agent.get('agent_slug') or agent.get('agent_id'),
        'description':    agent.get('description') or '',
        'visibility':     'private',
        'default_branch': 'main',
        'created_at':     agent.get('created_at', ''),
        'updated_at':     agent.get('updated_at', ''),
        'owner_id':       agent.get('user_id'),
        'status':         agent.get('status', 'active'),
        # keep raw agent fields too
        '_agent':         agent,
    }


def get_sources_status():
    """Connection status for the GUI header."""
    supabase_on = _db() is not None
    chroma_on, chroma_count = False, 0
    try:
        stats = gitmem_app.vector_engine.get_stats()
        chroma_count = stats.get('embeddings', 0) or 0
        freshness = stats.get('freshness', '')
        chroma_on = gitmem_app.vector_engine.client is not None and freshness in ('Connected', 'Volatile')
    except Exception:
        pass
    return {
        'supabase':       supabase_on,
        'chromadb':       chroma_on,
        'chromadb_count': chroma_count,
        'mcp':            True,
        'local_count':    0,
    }


# ── Landing ─────────────────────────────────────────────────────────────────────

@gitmem_bp.route('/')
@login_required
def landing():
    """
    GitMem Dashboard — one card per agent (= one repository).
    Fetches from api_agents WHERE user_id = current_user, then enriches
    each card with memory count, commit count, and vector count.
    """
    agents_raw = []
    if _db():
        try:
            res = _db().table('api_agents') \
                .select('*') \
                .eq('user_id', current_user.id) \
                .order('created_at', desc=True) \
                .execute()
            agents_raw = res.data or []
        except Exception as e:
            print(f"[GitMem] landing: failed to fetch agents: {e}")
            flash("Could not load agents from database.", "warning")

    # Enrich each agent with counts
    repos = []
    total_memories = 0
    total_commits = 0
    for agent in agents_raw:
        aid = agent.get('agent_id')
        mem_count    = _get_memory_count(aid)
        commit_count = _get_commit_count(aid)
        vector_stats = {}
        try:
            vector_stats = gitmem_app.vector_engine.get_agent_stats(aid)
        except Exception:
            pass

        repo = _agent_to_repo(agent)
        repo['memory_count']  = mem_count
        repo['commit_count']  = commit_count
        repo['vector_count']  = vector_stats.get('embeddings', 0)
        repos.append(repo)
        total_memories += mem_count
        total_commits  += commit_count

    stats = {
        'active_workspaces':  1,          # placeholder — no workspace concept in V1
        'total_repositories': len(repos),
        'total_memories':     total_memories,
        'total_commits':      total_commits,
    }

    return render_template(
        'landing.html',
        repos=repos,
        workspaces=[],
        stats=stats,
        sources=get_sources_status()
    )


# ── Agent / Repo Dashboard ───────────────────────────────────────────────────────

@gitmem_bp.route('/agent/<agent_id>')
@login_required
def agent_dashboard(agent_id):
    """
    Per-agent repo view.
    Ownership check: agent must belong to current_user.
    """
    if not _db():
        flash("Database disconnected", "error")
        return redirect(url_for('gitmem.landing'))

    # 1. Fetch and authorise
    agent = _get_agent(agent_id, user_id=current_user.id)
    if not agent:
        flash("Repository not found or access denied.", "error")
        return redirect(url_for('gitmem.landing'))

    # 2. Memories (latest 50)
    memories = []
    try:
        mem_res = _db().table('gitmem_memories') \
            .select('*').eq('agent_id', agent_id) \
            .order('created_at', desc=True).limit(50).execute()
        memories = mem_res.data or []
    except Exception as e:
        print(f"[GitMem] agent_dashboard: memories error: {e}")

    # 3. Commits (latest 20)
    commits = []
    try:
        commit_res = _db().table('gitmem_commits') \
            .select('*').eq('agent_id', agent_id) \
            .order('timestamp', desc=True).limit(20).execute()
        commits = commit_res.data or []
    except Exception as e:
        print(f"[GitMem] agent_dashboard: commits error: {e}")

    latest_commit = commits[0] if commits else None

    # 4. Branches from gitmem_refs (agent_id == repo_id in refs table)
    branches = []
    try:
        branches = gitmem_app.vcs.branch_manager.list_branches(agent_id)
    except Exception:
        pass

    # 5. Normalise to repo shape for template
    repo = _agent_to_repo(agent)
    repo['memory_count'] = len(memories)
    repo['commit_count'] = len(commits)

    return render_template(
        'repo_dashboard.html',
        repo=repo,
        branches=branches,
        memories=memories,
        commits=commits,
        latest_commit=latest_commit,
        sources=get_sources_status()
    )


# Keep /repo/<id> working too (for future V2 repos)
@gitmem_bp.route('/repo/<repo_id>')
@login_required
def repo_dashboard(repo_id):
    return redirect(url_for('gitmem.agent_dashboard', agent_id=repo_id))


# ── Create Agent ─────────────────────────────────────────────────────────────────

@gitmem_bp.route('/new', methods=['GET'])
@login_required
def create_agent_form():
    """Render the new-agent form."""
    return render_template('create_agent.html', workspaces=[], sources=get_sources_status())


@gitmem_bp.route('/api/create-agent', methods=['POST'])
@login_required
def api_create_agent():
    """
    Create a new Agent in api_agents.
    Maps form fields:  agent_id → agent_slug,  name → agent_name
    """
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
        agent_id, _row = svc.create_agent(
            user_id=current_user.id,
            agent_name=agent_name,
            agent_slug=agent_slug,
            description=description,
            permissions={"read": True, "write": True},
            limits={"max_memories": 10000},
            metadata={
                "llm_config": {},
                "capabilities": [],
                "status": "active",
            },
        )

        # Also create the default branch ref so VCS works immediately
        try:
            gitmem_app.vcs.branch_manager.create_branch(agent_id, 'main', 'HEAD', current_user.id)
        except Exception:
            pass

        flash(f"Repository '{agent_name}' created.", "success")
        return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))

    except Exception as e:
        flash(f"Failed to create repository: {e}", "error")
        return redirect(url_for('gitmem.create_agent_form'))


# ── API Endpoints ─────────────────────────────────────────────────────────────────

@gitmem_bp.route('/api/search')
@login_required
def api_search():
    """Semantic search within an agent's memory."""
    query   = request.args.get('q', '').strip()
    agent_id = request.args.get('repo_id') or request.args.get('agent_id')

    if not query or not agent_id:
        return jsonify({"error": "Missing parameters: q, repo_id (or agent_id)"}), 400

    # Ownership check — agent must belong to current_user
    agent = _get_agent(agent_id, user_id=current_user.id)
    if not agent:
        return jsonify({"error": "Access denied or agent not found"}), 403

    # Use retrieval orchestrator directly (bypass workspace RBAC for V1 agents)
    try:
        result = gitmem_app.retrieval.retrieve(
            query=query,
            repo_id=agent_id,
            agent_id=agent_id,
            max_tokens=2000
        )
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@gitmem_bp.route('/api/sync-sources', methods=['POST'])
@login_required
def api_sync_sources():
    """Re-sync vector store stats."""
    try:
        stats = gitmem_app.vector_engine.get_stats()
        return jsonify({"status": "ok", "stats": stats})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
