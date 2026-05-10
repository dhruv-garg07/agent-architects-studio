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
        chroma_count = stats.get('embeddings', 0)
        chroma_on = str(stats.get('freshness')) == 'Connected'
    except Exception:
        pass

    return {
        'supabase': supabase_on,
        'chromadb': chroma_on,
        'chromadb_count': chroma_count,
        'mcp': True, 
        'local_count': 0 # V2 doesn't use local fs
    }

@gitmem_bp.route('/')
@login_required
def landing():
    """GitMem V2 Dashboard - Shows Workspaces and Repositories."""
    # 1. Get User's Workspaces
    workspaces = gitmem_app.workspace_manager.get_user_workspaces(current_user.id)
    
    # 2. Get Repositories for all Workspaces
    repos = []
    if gitmem_app.supabase_client:
        try:
            ws_ids = [w['workspace_id'] for w in workspaces]
            if ws_ids:
                res = gitmem_app.supabase_client.table('gitmem_repos').select('*').in_('workspace_id', ws_ids).execute()
                repos = res.data or []
        except Exception as e:
            print(f"Error fetching repos: {e}")

    # 3. Stats
    stats = {
        'active_workspaces': len(workspaces),
        'total_repositories': len(repos),
        'total_memories': 0, # Requires aggregation query
        'total_commits': 0
    }

    return render_template('landing.html', workspaces=workspaces, repos=repos, stats=stats, sources=get_sources_status())

@gitmem_bp.route('/repo/<repo_id>')
@login_required
def repo_dashboard(repo_id):
    """View a specific repository's branches and memories."""
    # Validate access
    if not gitmem_app.supabase_client:
        flash("Database disconnected", "error")
        return redirect(url_for('gitmem.landing'))
        
    try:
        # Get Repo
        res = gitmem_app.supabase_client.table('gitmem_repos').select('*').eq('repo_id', repo_id).execute()
        if not res.data:
            flash("Repository not found", "error")
            return redirect(url_for('gitmem.landing'))
        repo = res.data[0]
        
        # Check permission
        if not gitmem_app.rbac_engine.check_permission(current_user.id, repo['workspace_id'], "repo:read", repo_id):
            flash("Access denied", "error")
            return redirect(url_for('gitmem.landing'))
            
        # Get Branches
        branches = gitmem_app.vcs.branch_manager.list_branches(repo_id, repo['workspace_id'])
        
        # Get Memories (Latest)
        mem_res = gitmem_app.supabase_client.table('gitmem_memories').select('*').eq('repo_id', repo_id).order('created_at', desc=True).limit(50).execute()
        memories = mem_res.data or []
        
        return render_template('repo_dashboard.html', repo=repo, branches=branches, memories=memories, sources=get_sources_status())
    except Exception as e:
        flash(f"Error loading repository: {e}", "error")
        return redirect(url_for('gitmem.landing'))

@gitmem_bp.route('/api/search')
@login_required
def api_search():
    """API endpoint for hybrid search via Retrieval Orchestrator."""
    query = request.args.get('q', '')
    repo_id = request.args.get('repo_id')
    workspace_id = request.args.get('workspace_id')
    
    if not all([query, repo_id, workspace_id]):
        return jsonify({"error": "Missing parameters"}), 400
        
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
