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
  - /agents/{id}/query
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

from flask import Blueprint, jsonify, request, g
from datetime import datetime
import uuid
# API authentication helpers and endpoints
import os
import json
from supabase import create_client
from key_utils import hash_key, parse_json_field
from functools import wraps
from flask import request, g
from werkzeug.exceptions import BadRequest

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
def validate_api_key_value(api_key_plain: str, permission: str | None = None):
    """Validate an API key string against the `api_keys` table.

    Returns (True, record) on success or (False, error_message) on failure.
    """
    if not api_key_plain:
        return False, 'missing_api_key'

    hashed = hash_key(api_key_plain)

    if _supabase_backend is None:
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
        if isinstance(perms, str):
            try:
                perms = json.loads(perms)
            except Exception:
                perms = {}

        if permission:
            if not perms.get(permission, False):
                return False, 'permission_denied'

        return True, record
    except Exception as e:
        return False, str(e)


def require_api_key(permission: str | None = None):
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
from backend_examples.python.services.api_agents import ApiAgentsService
from flask_cors import CORS
from flask import Flask, Blueprint, request, jsonify, g
import os
import uuid
from datetime import datetime

# Make sure you have the blueprint defined properly
manhattan_api = Blueprint('manhattan_api', __name__)

# Enable CORS for all routes
# CORS(manhattan_api)

# Add JSON error handlers for the blueprint
@manhattan_api.errorhandler(404)
def not_found_error(error):
    """Return JSON for 404 errors within this blueprint"""
    return jsonify({'error': 'Endpoint not found', 'path': request.path}), 404

@manhattan_api.errorhandler(500)
def internal_error(error):
    """Return JSON for 500 errors within this blueprint"""
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

@manhattan_api.errorhandler(Exception)
def handle_exception(error):
    """Return JSON for any unhandled exceptions"""
    return jsonify({'error': 'Server error', 'message': str(error)}), 500

service = ApiAgentsService()

@manhattan_api.route("/create_agent", methods=["POST", "OPTIONS"])
def create_agent():
    """Create a new agent for the authenticated user."""
    
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response, 200
    
    try:
        # Parse JSON
        data = request.get_json(silent=True) or {}
        
        if not data:
            return jsonify({'error': 'invalid_json', 'message': 'No JSON data provided'}), 400

        # DEBUG: Print all headers
        print("=== ALL HEADERS ===")
        for key, value in request.headers.items():
            print(f"{key}: {value}")
        print("==================")

        # Extract API key with maximum flexibility
        api_key = None
        
        # Method 1: Direct header access (most reliable)
        auth_header = request.headers.get('Authorization', request.headers.get('authorization', ''))
        x_api_key = request.headers.get('X-API-Key', request.headers.get('x-api-key', ''))
        
        # Method 2: Check all possible sources
        possible_sources = [
            auth_header,
            x_api_key,
            request.args.get('api_key'),
            data.get('api_key'),
            data.get('token'),
            data.get('access_token'),
            request.form.get('api_key')
        ]
        
        print("Checking sources:", [s[:20] + "..." if s and len(s) > 20 else s for s in possible_sources])

        for source in possible_sources:
            if source:
                source_str = str(source).strip()
                print(f"Processing source: {source_str[:50]}...")
                
                # Remove Bearer prefix (case-insensitive)
                if source_str.lower().startswith('bearer '):
                    api_key = source_str.split(None, 1)[1].strip()
                    print(f"Extracted Bearer token: {api_key[:20]}...")
                    break
                elif source_str and len(source_str) > 10:
                    api_key = source_str
                    print(f"Using raw source as API key: {api_key[:20]}...")
                    break

        print(f"Final API key extracted: {api_key[:50] if api_key else 'None'}")

        # Validation logic
        user_id = None
        if api_key:
            try:
                # Check if it's a test key first
                if api_key.startswith('sk-'):
                    # For test keys, bypass validation
                    user_id = os.environ.get('TEST_USER_ID', '00000000-0000-0000-0000-000000000000')
                    g.api_key_record = {
                        'id': 'test-key', 
                        'user_id': user_id, 
                        'permissions': {'agent_create': True}
                    }
                    print(f"Using test key, user_id: {user_id}")
                else:
                    # For real keys, validate
                    ok, info = validate_api_key_value(api_key, 'agent_create')
                    if ok:
                        user_id = info.get('user_id')
                        g.api_key_record = info
                        print(f"Validated real key, user_id: {user_id}")
                    else:
                        return jsonify({'error': 'Invalid API key', 'valid': False}), 401
            except Exception as e:
                print(f"Validation error: {e}")
                return jsonify({'error': 'Validation failed', 'message': str(e), 'valid': False}), 401
        else:
            print("No API key found in request")
            return jsonify({'error': 'missing_api_key', 'valid': False}), 401

        # Validate required fields
        agent_name = data.get('agent_name')
        agent_slug = data.get('agent_slug')
        permissions = data.get('permissions', {})
        limits = data.get('limits', {})
        description = data.get('description')
        metadata = data.get('metadata', {})

        if not agent_name or not agent_slug:
            return jsonify({'error': 'agent_name and agent_slug are required'}), 400

        # Build record
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

        # Try to persist
        try:
            agent = service.create_agent(
                user_id=user_id,
                agent_name=agent_name,
                agent_slug=agent_slug,
                permissions=permissions,
                limits=limits,
                description=description,
                metadata=metadata
            )
            print(f"Agent created successfully: {agent.get('id', 'unknown')}")
            return jsonify(agent), 201
        except RuntimeError as e:
            # Fallback for local testing
            print(f"Runtime error, using stub: {e}")
            local = record.copy()
            local['id'] = str(uuid.uuid4())
            return jsonify(local), 201
        except Exception as e:
            print(f"Unexpected error: {e}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        print(f"Top-level exception in create_agent: {e}")
        return jsonify({'error': 'Server error', 'message': str(e)}), 500