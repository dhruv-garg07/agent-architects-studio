from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
import os

from gitmem.core.app import gitmem_app

gitmem_bp = Blueprint('gitmem', __name__, url_prefix='/gitmem', template_folder='../../templates/gitmem')


def get_sources_status():
    """Check connections for the GUI header."""
    supabase_on = gitmem_app.supabase_client is not None
    chroma_on = False
    chroma_count = 0
    try:
        stats = gitmem_app.vector_engine.get_stats()
        chroma_count = stats.get('embeddings', 0) or 0
        # "Connected" = cloud, "Volatile" = local ephemeral, anything else = off
        freshness = stats.get('freshness', '')
        chroma_on = gitmem_app.vector_engine.client is not None and freshness in ('Connected', 'Volatile')
    except Exception:
        pass

    return {
        'supabase': supabase_on,
        'chromadb': chroma_on,
        'chromadb_count': chroma_count,
        'mcp': True,
        'local_count': 0
    }


# ============================================================
# Landing — Repository list (GitHub profile style)
# ============================================================

@gitmem_bp.route('/')
@login_required
def landing():
    """GitMem V2 Dashboard — Shows Repos (GitHub-style card grid)."""
    workspaces = gitmem_app.workspace_manager.get_user_workspaces(current_user.id)

    repos = []
    if gitmem_app.supabase_client:
        try:
            ws_ids = [w['workspace_id'] for w in workspaces]
            if ws_ids:
                res = gitmem_app.supabase_client.table('gitmem_repos').select('*').in_('workspace_id', ws_ids).execute()
                repos = res.data or []
        except Exception as e:
            print(f"[GitMem] Error fetching repos: {e}")

    stats = {
        'active_workspaces': len(workspaces),
        'total_repositories': len(repos),
        'total_memories': 0,
        'total_commits': 0,
    }

    return render_template(
        'landing.html',
        repos=repos,
        workspaces=workspaces,
        stats=stats,
        sources=get_sources_status()
    )


# ============================================================
# Repo Dashboard (GitHub repo page)
# ============================================================

@gitmem_bp.route('/repo/<repo_id>')
@login_required
def repo_dashboard(repo_id):
    """View a specific repository — branches, memories, commits."""
    if not gitmem_app.supabase_client:
        flash("Database disconnected", "error")
        return redirect(url_for('gitmem.landing'))

    try:
        res = gitmem_app.supabase_client.table('gitmem_repos').select('*').eq('repo_id', repo_id).execute()
        if not res.data:
            flash("Repository not found", "error")
            return redirect(url_for('gitmem.landing'))
        repo = res.data[0]

        if not gitmem_app.rbac_engine.check_permission(current_user.id, repo['workspace_id'], "repo:read", repo_id):
            flash("Access denied", "error")
            return redirect(url_for('gitmem.landing'))

        branches = gitmem_app.vcs.branch_manager.list_branches(repo_id, repo['workspace_id'])

        mem_res = gitmem_app.supabase_client.table('gitmem_memories') \
            .select('*').eq('repo_id', repo_id) \
            .order('created_at', desc=True).limit(50).execute()
        memories = mem_res.data or []

        # Fetch recent commits
        commit_res = gitmem_app.supabase_client.table('gitmem_commits') \
            .select('*').eq('repo_id', repo_id) \
            .order('timestamp', desc=True).limit(20).execute()
        commits = commit_res.data or []
        latest_commit = commits[0] if commits else None

        return render_template(
            'repo_dashboard.html',
            repo=repo,
            branches=branches,
            memories=memories,
            commits=commits,
            latest_commit=latest_commit,
            sources=get_sources_status()
        )
    except Exception as e:
        flash(f"Error loading repository: {e}", "error")
        return redirect(url_for('gitmem.landing'))


# ============================================================
# Agent Dashboard — alias for repo_dashboard (backward compat)
# ============================================================

@gitmem_bp.route('/agent/<agent_id>')
@login_required
def agent_dashboard(agent_id):
    """Agent view — looks up the repo by agent_id and forwards to repo_dashboard."""
    if not gitmem_app.supabase_client:
        flash("Database disconnected", "error")
        return redirect(url_for('gitmem.landing'))

    try:
        # In V2, agent_id maps to repo_id
        res = gitmem_app.supabase_client.table('gitmem_repos').select('*').eq('repo_id', agent_id).execute()
        if not res.data:
            flash("Repository not found for this agent", "error")
            return redirect(url_for('gitmem.landing'))
        repo = res.data[0]

        if not gitmem_app.rbac_engine.check_permission(current_user.id, repo['workspace_id'], "repo:read", agent_id):
            flash("Access denied", "error")
            return redirect(url_for('gitmem.landing'))

        branches = gitmem_app.vcs.branch_manager.list_branches(agent_id, repo['workspace_id'])
        mem_res = gitmem_app.supabase_client.table('gitmem_memories') \
            .select('*').eq('repo_id', agent_id) \
            .order('created_at', desc=True).limit(50).execute()
        memories = mem_res.data or []

        commit_res = gitmem_app.supabase_client.table('gitmem_commits') \
            .select('*').eq('repo_id', agent_id) \
            .order('timestamp', desc=True).limit(20).execute()
        commits = commit_res.data or []
        latest_commit = commits[0] if commits else None

        # Build agent-like object from repo for backward compat with agent_dashboard.html
        agent = {
            'id': repo.get('repo_id'),
            'name': repo.get('name'),
            'description': repo.get('description', ''),
            'status': 'online',
        }

        context_sources = []

        return render_template(
            'agent_dashboard.html',
            agent=agent,
            repo=repo,
            branches=branches,
            memories=memories,
            commits=commits,
            latest_commit=latest_commit,
            context_sources=context_sources,
            sources=get_sources_status()
        )
    except Exception as e:
        flash(f"Error loading agent view: {e}", "error")
        return redirect(url_for('gitmem.landing'))


# ============================================================
# Create Agent + Repo Form
# ============================================================

@gitmem_bp.route('/new', methods=['GET'])
@login_required
def create_agent_form():
    """Render the form to create a new Agent + Repository."""
    workspaces = gitmem_app.workspace_manager.get_user_workspaces(current_user.id)
    return render_template('create_agent.html', workspaces=workspaces, sources=get_sources_status())


@gitmem_bp.route('/api/create-agent', methods=['POST'])
@login_required
def api_create_agent():
    """Create a new Agent profile + backing Repository."""
    data = request.form if request.form else request.get_json(silent=True) or {}

    agent_id = data.get('agent_id', '').strip()
    name = data.get('name', agent_id).strip()
    description = data.get('description', '').strip()
    workspace_id = data.get('workspace_id', '').strip()

    if not agent_id:
        flash("Agent ID is required", "error")
        return redirect(url_for('gitmem.create_agent_form'))

    if not workspace_id:
        # Use the first available workspace or return error
        workspaces = gitmem_app.workspace_manager.get_user_workspaces(current_user.id)
        if not workspaces:
            flash("You must belong to a workspace first", "error")
            return redirect(url_for('gitmem.create_agent_form'))
        workspace_id = workspaces[0]['workspace_id']

    if not gitmem_app.supabase_client:
        flash("Database disconnected", "error")
        return redirect(url_for('gitmem.create_agent_form'))

    try:
        # 1. Create the Repo record
        from gitmem.core.models import Repo
        import re
        slug = re.sub(r'[^a-z0-9\-]', '-', agent_id.lower()).strip('-')
        repo = Repo(
            repo_id=agent_id,
            workspace_id=workspace_id,
            name=name,
            slug=slug,
            description=description,
            owner_id=current_user.id,
        )
        gitmem_app.supabase_client.table('gitmem_repos').insert(repo.model_dump(mode='json')).execute()

        # 2. Create the default branch
        gitmem_app.vcs.branch_manager.create_branch(agent_id, 'main', 'HEAD', current_user.id)

        flash(f"Repository '{name}' created successfully", "success")
        return redirect(url_for('gitmem.agent_dashboard', agent_id=agent_id))
    except Exception as e:
        flash(f"Failed to create repository: {e}", "error")
        return redirect(url_for('gitmem.create_agent_form'))


# ============================================================
# API Endpoints
# ============================================================

@gitmem_bp.route('/api/search')
@login_required
def api_search():
    """Hybrid semantic search via Retrieval Orchestrator."""
    query = request.args.get('q', '')
    repo_id = request.args.get('repo_id')
    workspace_id = request.args.get('workspace_id')

    if not all([query, repo_id, workspace_id]):
        return jsonify({"error": "Missing parameters: q, repo_id, workspace_id"}), 400

    if not gitmem_app.rbac_engine.check_permission(current_user.id, workspace_id, "repo:read", repo_id):
        return jsonify({"error": "Access denied"}), 403

    res = gitmem_app.command_handler.execute(
        command_name="retrieve_context",
        actor_id=current_user.id,
        workspace_id=workspace_id,
        payload={
            "repo_id": repo_id,
            "query": query,
            "max_tokens": 2000
        }
    )

    return jsonify(res)


@gitmem_bp.route('/api/sync-sources', methods=['POST'])
@login_required
def api_sync_sources():
    """Trigger a re-sync of all data sources."""
    try:
        # Re-initialize vector engine stats
        stats = gitmem_app.vector_engine.get_stats()
        return jsonify({"status": "ok", "stats": stats})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
