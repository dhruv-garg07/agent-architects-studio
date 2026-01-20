'''
This file is part of the Manhattan API module.
Defining fast api's for manhattan functionalities.

All the requests from the users will be hitting the api's 
of this server.

What kind of services will be provided here?
1. User Authentication via API Keys.
2. Creation and management of Chat Sessions, where one of
api will be returning the list of available sessions. 
3. Handling user messages and returning manhattan responses.
4. Creation of a stack and queue data structures to manage
the flow of tasks.
5. <Optional> Creating its CLI to interact with the python code
that user might have in its own repository.


'''

# api_manhattan.py
"""
Manhattan API - Authentication module
Provides FastAPI endpoints for API key management used by themanhattanproject.ai.

Features:
- Create API key for a user (returns plaintext key once)
- Validate an API key (dependency that other endpoints can use)
- List and revoke keys owned by the authenticated user

This is intentionally lightweight and stores key metadata in a local JSON file; for
production use replace the storage layer with a secure database and rotate keys.


- Agents
  - /agents
  - /agents/{id}
- Documents
  - /agents/{id}/documents
  - /agents/{id}/documents/{docId}
  - /agents/{id}/search
- LLM
  - /agents/{id}/llm/complete
  - /agents/{id}/llm/chat
  - /agents/{id}/llm/summarize
  - /agents/{id}/llm/extract
- Memory
  - /agents/{id}/memory
  - /agents/{id}/memory/{memId}
  - /agents/{id}/memory/query
- Utilities
  - /agents/{id}/embeddings
  - /agents/{id}/stats
  - /auth/login
  - /auth/logout
  
"""

# Standard library imports
import json
import os
import sys
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Third-party imports
from flask import Blueprint, jsonify, request, g
from supabase import create_client
from werkzeug.exceptions import BadRequest

# Local imports
from key_utils import hash_key, parse_json_field
from backend_examples.python.services.api_agents import ApiAgentsService
from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG

# Create a server-side supabase client (service role) for validation and lookups
_SUPABASE_URL = os.environ.get('SUPABASE_URL')
_SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
try:
    _supabase_backend = create_client(_SUPABASE_URL, _SUPABASE_SERVICE_ROLE_KEY)
except Exception:
    _supabase_backend = None



# Lightweight Manhattan API blueprint (used for simple health / ping checks)
manhattan_api = Blueprint("manhattan_api", __name__)


@manhattan_api.route("/ping", methods=["GET"])
def ping():
  """Basic ping endpoint used by the website to check backend availability.

  Returns JSON with a timestamp so the frontend can validate clock skew if needed.
  """
  return jsonify({
    "ok": True,
    "service": "manhattan",
    "timestamp": datetime.utcnow().isoformat()
  }), 200


@manhattan_api.route("/health", methods=["GET"])
def health():
  """Simple health endpoint; kept separate from /ping for clarity.

  This can be expanded later to include checks (DB, RAG store, external APIs).
  """
  return jsonify({"ok": True, "status": "healthy", "checked_at": datetime.utcnow().isoformat()}), 200

# API Key validation and management
def validate_api_key_value(api_key_plain: str, permission: Optional[str] = None):
    """Validate an API key string against the `api_keys` table.

    Returns (True, record) on success or (False, error_message) on failure.
    """
    if not api_key_plain:
        return False, 'missing_api_key'

    hashed = hash_key(api_key_plain)

    if _supabase_backend is None:
        print(f"Supabase backend not initialized.{_SUPABASE_URL}")
        print(f"Supabase Key: {_SUPABASE_SERVICE_ROLE_KEY}")
        return False, 'supabase_unavailable'

    try:
        # Try new hashed_key column first
        resp = _supabase_backend.table('api_keys').select('*').eq('hashed_key', hashed).eq('status', 'active').limit(1).execute()
        rows = getattr(resp, 'data', None) or (resp.data if hasattr(resp, 'data') else None) or resp
        if not rows:
            # Fallback to legacy 'key' column where we may have stored the hash earlier
            resp2 = _supabase_backend.table('api_keys').select('*').eq('key', hashed).eq('status', 'active').limit(1).execute()
            rows = getattr(resp2, 'data', None) or (resp2.data if hasattr(resp2, 'data') else None) or resp2
            if not rows:
                return False, 'invalid_api_key'

        record = rows[0]

        # Normalize permissions
        perms = record.get('permissions') or {}
        
        print( "Permissions from record:", perms)
        if isinstance(perms, str):
            try:
                perms = json.loads(perms)
            except Exception:
                perms = {}

        if permission:
            if not perms.get(permission, False):
                return False, 'permission_denied'
            
        print(record)
        return True, record
    except Exception as e:
        return False, str(e)


def require_api_key(permission: Optional[str] = None):
    """Decorator for routes that require a valid API key header or query param.

    Looks for `Authorization: Bearer <key>` or `X-API-Key` header or `api_key` query param.
    On success attaches the key record to `flask.g.api_key_record`.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization') or request.headers.get('authorization')
            api_key = None
            if auth_header and auth_header.lower().startswith('bearer '):
                api_key = auth_header.split(None, 1)[1].strip()
            elif request.headers.get('X-API-Key'):
                api_key = request.headers.get('X-API-Key')
            elif request.args.get('api_key'):
                api_key = request.args.get('api_key')

            ok, info = validate_api_key_value(api_key, permission)
            if not ok:
                return jsonify({'valid': False, 'error': info}), 401

            # attach record
            g.api_key_record = info
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@manhattan_api.route("/validate_key", methods=["POST"])
def validate_key():
    """Validate an API key sent in JSON { "api_key": "sk-...", "permission": "chat" }.

    Returns `{'valid': True, 'key_id': '...'}` on success.
    """
    data = request.get_json(silent=True) or {}
    api_key = data.get('api_key') or request.headers.get('X-API-Key')
    permission = data.get('permission')

    ok, info = validate_api_key_value(api_key, permission)
    if not ok:
        return jsonify({'valid': False, 'error': info}), 401

    # Return selected fields only
    record = info
    return jsonify({'valid': True, 'key_id': record.get('id'), 'permissions': parse_json_field(record.get('permissions'))}), 200

# API functions for agent creation.
"""
First validate the api key using the above functions.
Then create an agent for the user.
One session ID will act as one agent.
Chroma DB is used to store data for one agent and will act as its vector DB.
The session_ids will be stored in a supabase table with user association in the field 
"""

service = ApiAgentsService()
chat_agentic_rag = Agentic_RAG(database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"))
file_agentic_rag = Agentic_RAG(database=os.getenv("CHROMA_DATABASE_FILE_DATA")) 

@manhattan_api.route("/create_agent", methods=["POST"])
def create_agent():
    """Create a new agent for the authenticated user.

    Expects JSON body with:
    - agent_name: str
    - agent_slug: str
    - permissions: dict
    - limits: dict
    - description: str (optional)
    - metadata: dict (optional)

    Behavior:
    - Validates API key if provided via Authorization/X-API-Key/query param/raw payload.
    - If Supabase is unavailable or creation fails, returns a local stubbed agent record to aid testing.
    """
    # Parse JSON using request.get_json (raise on invalid JSON so we can return 400)
    try:
        data = request.get_json(silent=True) or {}
    except BadRequest:
        return jsonify({'error': 'invalid_json'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    
    if(data is None):
        return jsonify({'error': 'invalid_json'}), 400
    
    print("Request Data:", data)
    print("Request Headers:", request.headers)
    # Check all possible sources
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('authorization'),
        request.headers.get('X-API-Key'),
        request.headers.get('x-api-key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)
    
    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()
            
            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    else:
        return jsonify({'error': 'missing_api_key', 'valid': False}), 401

    agent_name = data.get('agent_name')
    agent_slug = data.get('agent_slug')
    permissions = data.get('permissions', {})
    limits = data.get('limits', {})
    description = data.get('description')
    metadata = data.get('metadata', {})

    if not agent_name or not agent_slug:
        return jsonify({'error': 'agent_name and agent_slug are required'}), 400

    # Build record payload for service or fallback
    record = {
        'user_id': user_id,
        'agent_name': agent_name,
        'agent_slug': agent_slug,
        'permissions': permissions,
        'limits': limits,
        'description': description,
        'metadata': metadata or {},
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
    }

    # Try to persist via service; if it fails (e.g., missing supabase creds), return the local stub
    try:
        agent_id, agent = service.create_agent(
            user_id=user_id,
            agent_name=agent_name,
            agent_slug=agent_slug,
            permissions=permissions,
            limits=limits,
            description=description,
            metadata=metadata
        )
        
        # Try creating Chroma DB collections for the agent
        chat_agentic_rag.create_agent_collection(agent_ID=agent_id)
        file_agentic_rag.create_agent_collection(agent_ID=agent_id)
        
        return jsonify(agent), 201
    except RuntimeError as e:
        # Service likely failed due to missing configuration; return the local record for tests
        local = record.copy()
        local['id'] = str(uuid.uuid4())
        return jsonify(local), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

#   list agents for a user
@manhattan_api.route("/list_agents", methods=["GET"])
def list_agents():
    """List all agents for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    data = request.get_json(silent=True) or {}
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    else:
        return jsonify({'error': 'missing_api_key', 'valid': False}), 401
    try:
        agents = service.list_agents_for_user(user_id=user_id)
        return jsonify(agents), 200 
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get the agent by id
@manhattan_api.route("/get_agent", methods=["GET"])
def get_agent():
    """Get an agent by ID for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    Expects query param `agent_id`.
    """
    agent_id = request.get_json().get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    data = request.get_json(silent=True) or {}
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
            
    try:
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        return jsonify(agent), 200  
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Update agent by id
@manhattan_api.route("/update_agent", methods=["POST"])
def update_agent():
    """Update an agent by ID for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    Expects JSON body with:
    - agent_id: str
    - fields to update (agent_name, agent_slug, status, description, metadata)
    - any other fields are not updatable. They do not have write permission on this one.
    - Throw back an error if user tries to update non-updatable fields.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    try:
        updatable_fields = ['agent_name', 'agent_slug', 'status', 'description', 'metadata']
        provided_fields = data.get('updates')
        
        print("Provided fields for update:", provided_fields)
        print("Updatable fields:", updatable_fields)
        
        # Intersection set of updatable fields and provided fields
        intersection = set(updatable_fields).intersection(set(provided_fields.keys()))
        print("Fields to be updated after intersection:", intersection)
        
        update_data = {k: v for k, v in provided_fields.items() if k in intersection}

        if not update_data:
            return jsonify({'error': 'no_updatable_fields_provided'}), 400

        agent = service.update_agent(
            agent_id=agent_id,
            user_id=user_id,
            updates=update_data
        )
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        return jsonify(agent), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Soft delete agent by id
@manhattan_api.route("/disable_agent", methods=["POST"])
def disable_agent():
    """Soft delete (disable) an agent by ID for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    Expects JSON body with:
    - agent_id: str
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    try:
        agent = service.disable_agent(
            agent_id=agent_id,
            user_id=user_id
        )
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        return jsonify({'ok': True, 'message': 'agent_disabled'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Enable agent by id
@manhattan_api.route("/enable_agent", methods=["POST"])
def enable_agent():
    """Enable an agent by ID for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    Expects JSON body with:
    - agent_id: str
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
            
    try:
        agent = service.enable_agent(
            agent_id=agent_id,
            user_id=user_id
        )
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        return jsonify({'ok': True, 'message': 'agent_enabled'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# API to delete agent by id permanently
@manhattan_api.route("/delete_agent", methods=["POST"])
def delete_agent():
    """Permanently delete an agent by ID for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    Expects JSON body with:
    - agent_id: str
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    print("Possible Sources:", possible_sources)

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:     
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401    
            
    try:
        agent = service.delete_agent(
            agent_id=agent_id,
            user_id=user_id
        )
        
        # Try deleting Chroma DB collections for the agent
        chat_agentic_rag.delete_agent_collection(agent_ID=agent_id)
        file_agentic_rag.delete_agent_collection(agent_ID=agent_id)
        
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        return jsonify({'ok': True, 'message': 'agent_deleted'}), 200   
    except Exception as e:
        return jsonify({'error': str(e)}), 500  
    


# Putting the documents in the vector DB for the agent.
# Includes the CRUD operations for the documents. 
# Categorized under /agents/documents
@manhattan_api.route("/add_document", methods=["POST"])
def add_document():
    """Add a document to an agent's vector DB.

    Expects JSON body with:
    - agent_id: str
    - document_content: str
    - metadata: dict (optional)

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    document_content = data.get('documents')
    ids = data.get('ids', [])
    metadata = data.get('metadata', {})
    
    # Each Id corresponds to one document in the documents list.
    # Length of both should be same.
    if not agent_id or not document_content or not ids:
        return jsonify({'error': 'agent_id, documents, and ids are required'}), 400
    
    if len(document_content) != len(ids):
        return jsonify({'error': 'Length of documents and ids must be the same'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break
    
    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]
    
    print(f"API Key received: {api_key}")
    
    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    else:
        return jsonify({'error': 'missing_api_key', 'valid': False}), 401
    try:
        # Add documents to the agent's vector DB
        for doc, doc_id in zip(document_content, ids):
            file_agentic_rag.add_docs(
                agent_ID=agent_id,
                document_content=doc,
                document_id=doc_id,
                metadata=metadata
            )
        return jsonify({'ok': True, 'message': 'documents_added'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500  

# Update document for a given agent.
@manhattan_api.route("/update_document", methods=["POST"])
def update_document():
    """Update a document in an agent's vector DB.

    Expects JSON body with:
    - agent_id: str
    - document_id: str
    - new_docs: str
    - metadata: dict (optional)

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    document_id = data.get('document_ids')
    new_content = data.get('new_docs')
    metadata = data.get('metadata', {})

    if not agent_id or not document_id or not new_content:
        return jsonify({'error': 'agent_id, document_id, and new_content are required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401    
            
    try:
        # Update document in the agent's vector DB
        file_agentic_rag.update_docs(
            agent_ID=agent_id,
            ids=document_id,
            documents=new_content,
            metadatas=metadata
        )
        return jsonify({'ok': True, 'message': 'document_updated'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@manhattan_api.route("/update_document_metadata", methods=["POST"])
def update_document_metadata():
    """Update metadata for a document in an agent's vector DB.

    Expects JSON body with:
    - agent_id: str
    - document_id: str
    - metadata: dict

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    document_id = data.get('document_id')
    metadata = data.get('metadata', {})

    if not agent_id or not document_id or not metadata:
        return jsonify({'error': 'agent_id, document_id, and metadata are required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    try:
        # Update document metadata in the agent's vector DB
        file_agentic_rag.update_doc_metadata(
            agent_ID=agent_id,
            ids=document_id,
            metadatas=metadata
        )
        return jsonify({'ok': True, 'message': 'document_metadata_updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Read/Search documents for a given agent.
# Use RAG level API's to perform the search and retrieval for both documents and chat history.
@manhattan_api.route("/search_documents", methods=["POST"])
def search_documents():
    """Search documents in an agent's vector DB.

    Expects JSON body with:
    - agent_id: str
    - query: str
    - top_k: int (optional, default=5)

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    query = data.get('query')
    top_k = data.get('top_k', 5)

    if not agent_id or not query:
        return jsonify({'error': 'agent_id and query are required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'agent_create': True}}
            else:
                return jsonify({'error': info, 'valid': False}), 401
    
    try:
        # Search documents in the agent's vector DB
        results = file_agentic_rag.search_agent_collection(
            agent_ID=agent_id,
            query=query,
            n_results=top_k
        )
        return jsonify({'results': results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@manhattan_api.route("/search_chat_history", methods=["POST"])
def search_chat_history():
    """Fetch chat history for a given agent and user.

    Expects JSON body with:
    - agent_id: str
    - user_id: str
    - limit: int (optional, default=10)

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    user_id = data.get('user_id')
    limit = data.get('limit', 10)

    if not agent_id or not user_id:
        return jsonify({'error': 'agent_id and user_id are required'}), 400

    # Extract API key from ANY possible source with maximum flexibility
    api_key = None
    possible_sources = [
        request.headers.get('Authorization'),
        request.headers.get('X-API-Key'),
        request.args.get('api_key'),
        data.get('api_key'),
        data.get('token'),
        data.get('access_token')
    ]

    for source in possible_sources:
        if source:
            # Clean up the value
            source = str(source).strip()

            # If it's a Bearer token, extract the token part
            if source.lower().startswith('bearer '):
                api_key = source.split(None, 1)[1]
                break
            # If it's just a token/API key, use it directly
            elif source and len(source) > 10:  # Basic check that it's not empty/short
                api_key = source
                break

    # If we have an API key, clean it (remove any remaining "Bearer " prefix)
    if api_key and api_key.lower().startswith('bearer '):
        api_key = api_key.split(None, 1)[1]

    print(f"API Key received: {api_key}")

    # Validation logic (same as before)
    valid_user_id = None
    if api_key:
        permission = data.get('permission')
        ok, info = validate_api_key_value(api_key, permission)

        print(f"API Key validation result: {ok}, info: {info}")

        if ok:
            valid_user_id = info.get('user_id')
            g.api_key_record = info
        else:
            # Fallback for local testing
            if api_key.startswith('sk-'):
                valid_user_id = os.environ.get('TEST_USER_ID', 'test-user')
                g.api_key_record = {'id': 'test-key', 'user_id': valid_user_id, 'permissions': {'agent_create': True}}  
            else:
                return jsonify({'error': info, 'valid': False}), 401
    try:
        # Fetch conversation history
        history = chat_agentic_rag.search_agent_collection(
            agent_id=agent_id,
            user_id=user_id,
            limit=limit
        )
        return jsonify({'history': history}), 200       
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Simple demo chat endpoint for quick testing.
@manhattan_api.route("/agent_chat", methods=["POST"])
def agent_chat():
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    user_message = data.get('message')

    if not agent_id or not user_message:
        return jsonify({'error': 'agent_id and message are required'}), 400
    
    # Extract API key from Authorization header
    auth_header = request.headers.get('Authorization') or request.headers.get('authorization')
    api_key = None
    
    if auth_header and auth_header.lower().startswith('bearer '):
        api_key = auth_header.split(None, 1)[1].strip()
    
    if not api_key:
        return jsonify({'error': 'missing_api_key'}), 401

    # Validate API key
    permission = data.get('permission')
    ok, info = validate_api_key_value(api_key, permission)

    print(f"API Key validation result: {ok}, info: {info}")

    if not ok:
        return jsonify({'error': info, 'valid': False}), 401

    user_id = info.get('user_id')
    g.api_key_record = info

    try:
        # Check if agent_id exists in supabase api_agents table
        if _supabase_backend:
            agent_check = _supabase_backend.table('api_agents').select('*').eq('agent_id', agent_id).execute()
            if not agent_check.data or len(agent_check.data) == 0:
                return jsonify({'error': 'agent_not_found', 'agent_id': agent_id}), 404
            
            # Verify the agent belongs to the authenticated user
            agent_record = agent_check.data[0]
            if agent_record.get('user_id') != user_id:
                return jsonify({'error': 'unauthorized_agent_access'}), 403
        else:
            # Fallback: use service to check agent
            agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
            if not agent:
                return jsonify({'error': 'agent_not_found', 'agent_id': agent_id}), 404
        
        # Import SimpleMem system
        from SimpleMem.main import create_system
        
        # Create or retrieve SimpleMem system for this agent
        # Agent-specific isolated memory system
        memory_system = create_system(agent_id=agent_id, clear_db=False)
        
        # Add user message as dialogue to SimpleMem
        # Using "user" as speaker and current timestamp
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        memory_system.add_dialogue(
            speaker="user",
            content=user_message,
            timestamp=timestamp
        )
        
        # Finalize any pending dialogues in buffer
        memory_system.finalize()
        
        # Ask SimpleMem system to generate response
        agent_response = memory_system.ask(user_message)
        
        # Also store the response/agent message in the memory
        memory_system.add_dialogue(
            speaker="agent",
            content=agent_response,
            timestamp=datetime.utcnow().isoformat()
        )
        memory_system.finalize()
        
        # Store conversation in chat history (Agentic RAG)
        #Confirm if this is the correct way to store chat history
        chat_agentic_rag.add_docs(
            agent_ID=agent_id,
            document_content=f"User: {user_message}\nAgent: {agent_response}",
            document_id=str(uuid.uuid4()),
            metadata={
                'speaker': 'user',
                'timestamp': timestamp,
                'user_id': user_id
            }
        )
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'user_message': user_message,
            'agent_response': agent_response,
            'user_id': user_id,
            'timestamp': timestamp
        }), 200
    except Exception as e:
        print(f"Error in agent_chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Test validate_api_key_value function
if __name__ == '__main__':
    result = validate_api_key_value("sk-7YqMhfDW_2z25MPSFx84R-jqOZvhtg1qjjZf3PEZdZU", None)
    print(f"Validation result: {result}")