"""
    This file calls all the necessary apis for the CRUD of agents created by the user both b y the api calls and the website.
    Th UI from the frontend shall support CRUD operations and the backend service will be used to update the supabase backend.\
    The HTML file that will call this api is dashboard.html where there is a tab on the left panel which has My Agents section.
    That section will call these apis to get the agents created by the user and display them in a list.
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from backend_examples.python.services.api_agents import ApiAgentsService
import os 
import json
from supabase import create_client
apis_my_agents = Blueprint('my_agents', __name__, url_prefix='/dashboard')

# Create a server-side supabase client (service role) for validation and lookups
_SUPABASE_URL = os.environ.get('SUPABASE_URL')
_SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
try:
    _supabase_backend = create_client(_SUPABASE_URL, _SUPABASE_SERVICE_ROLE_KEY)
except Exception:
    _supabase_backend = None
    

# Give the list of the agents in the database created by the user return a JSON response
@apis_my_agents.route('/agents', methods=['GET'])
@login_required
def get_my_agents():
    print('[DEBUG] Fetching agents for user:', current_user.get_id())
    try:
        user_id = current_user.get_id()
        api_agents_service = ApiAgentsService()
        agents = api_agents_service.list_agents_for_user(user_id)
        print('[DEBUG] Fetched agents for user:', user_id, agents)
        return jsonify({"status": "success", "data": agents}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Update/Delete/Confirm Buttons to be put as APIs here and will be sued in the JavaScript code in dashboard.html
# to call these APIs when the buttons are clicked.

@apis_my_agents.route('/update/<agent_id>', methods=['PUT'])
@login_required
def update_agent(agent_id):
    """Update an existing agent owned by the current user.

    Accepts a JSON body with any of the updatable fields. Only a subset of
    fields are allowed and will be forwarded to the service layer.
    """
    try:
        user_id = current_user.get_id()
        payload = request.get_json() or {}

        # Only allow a safe subset of fields to be updated from the client
        allowed_fields = {
            'agent_name', 'agent_slug', 'description', 'status',
            'permissions', 'limits', 'metadata'
        }

        updates = {k: v for k, v in payload.items() if k in allowed_fields}

        if not updates:
            return jsonify({"status": "error", "message": "No valid update fields provided"}), 400

        api_agents_service = ApiAgentsService()
        updated = api_agents_service.update_agent(agent_id=agent_id, user_id=user_id, updates=updates)

        return jsonify({"status": "success", "data": updated}), 200
    except Exception as e:
        # Log server-side error and return a 500 with message
        print('[ERROR] update_agent failed for user', current_user.get_id(), 'agent', agent_id, str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@apis_my_agents.route('/create', methods=['POST'])
@login_required
def create_agent():
    """Create a new agent for the current user.

    Expects JSON body containing at least: agent_name, agent_slug, permissions, limits
    Optional: description, metadata
    """
    try:
        user_id = current_user.get_id()
        payload = request.get_json() or {}

        required = ['agent_name', 'agent_slug', 'permissions', 'limits']
        missing = [k for k in required if not payload.get(k)]
        if missing:
            return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

        agent_name = payload.get('agent_name')
        agent_slug = payload.get('agent_slug')
        permissions = payload.get('permissions')
        limits = payload.get('limits')
        description = payload.get('description')
        metadata = payload.get('metadata')

        api_agents_service = ApiAgentsService()
        agent_id, created = api_agents_service.create_agent(
            user_id=user_id,
            agent_name=agent_name,
            agent_slug=agent_slug,
            permissions=permissions,
            limits=limits,
            description=description,
            metadata=metadata,
        )

        # Return the created record (service returns row data)
        return jsonify({"status": "success", "data": created}), 201
    except Exception as e:
        print('[ERROR] create_agent failed for user', current_user.get_id(), str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@apis_my_agents.route('/delete/<agent_id>', methods=['DELETE'])
@login_required
def delete_agent_route(agent_id):
    """Delete an agent owned by the current user.

    Uses the service layer to perform the deletion. Returns 200 on success,
    404 if the agent was not found or delete failed, and 500 on server error.
    """
    try:
        user_id = current_user.get_id()
        api_agents_service = ApiAgentsService()
        deleted = api_agents_service.delete_agent(agent_id=agent_id, user_id=user_id)

        if not deleted:
            return jsonify({"status": "error", "message": "Agent not found or delete failed"}), 404

        return jsonify({"status": "success", "message": "Agent deleted"}), 200
    except Exception as e:
        print('[ERROR] delete_agent failed for user', current_user.get_id(), 'agent', agent_id, str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
