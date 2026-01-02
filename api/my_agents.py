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