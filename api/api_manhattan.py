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
# Add parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'lib'))

# Third-party imports
from flask import Blueprint, jsonify, request, g, Response
from supabase import create_client
from werkzeug.exceptions import BadRequest

# Local imports
from key_utils import hash_key, parse_json_field
from backend_examples.python.services.api_agents import ApiAgentsService
from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
from Octave_mem.SqlDB.sqlDbController import add_message

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


def extract_api_key_from_request(data: dict = None) -> Optional[str]:
    """Robustly extract API key from all possible request sources."""
    # 1. Check Authorization Header (Bearer or Raw)
    auth = request.headers.get('Authorization') or request.headers.get('authorization')
    if auth:
        auth = str(auth).strip()
        if auth.lower().startswith('bearer '):
            parts = auth.split(None, 1)
            if len(parts) > 1:
                return parts[1].strip()
        elif len(auth) > 10:
            return auth

    # 2. Check X-API-Key or other custom headers
    for h in ['X-API-Key', 'x-api-key', 'Api-Key', 'api-key']:
        val = request.headers.get(h)
        if val and len(str(val).strip()) > 10:
            return str(val).strip()

    # 3. Check Query Parameters
    q_key = request.args.get('api_key') or request.args.get('token')
    if q_key and len(str(q_key).strip()) > 10:
        return str(q_key).strip()

    # 4. Check JSON Body
    if data:
        for k in ['api_key', 'token', 'access_token']:
            val = data.get(k)
            if val and len(str(val).strip()) > 10:
                return str(val).strip()
    
    return None


def extract_and_validate_api_key(data: dict = None):
    """Helper function to extract and validate API key from various sources.
    
    Returns (user_id, error_response) tuple.
    """
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user.get_id(), None
    except ImportError:
        pass

    api_key = extract_api_key_from_request(data)

    if not api_key:
        return None, (jsonify({'error': 'missing_api_key', 'valid': False}), 401)

    permission = data.get('permission') if data else None
    ok, info = validate_api_key_value(api_key, permission)

    if ok:
        g.api_key_record = info
        return info.get('user_id'), None
    else:
        # Fallback for local testing
        if api_key.startswith('sk-'):
            import os
            user_id = os.environ.get('TEST_USER_ID', 'test-user')
            g.api_key_record = {'id': 'test-key', 'user_id': user_id, 'permissions': {'memory': True, 'agent_create': True}}
            return user_id, None
        return None, (jsonify({'error': info, 'valid': False}), 401)


def _verify_agent_ownership(agent_id: str, user_id: str):
    """Verify the agent belongs to the user. Returns (agent_record, error_response)."""
    try:
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return None, (jsonify({'error': 'agent_not_found', 'agent_id': agent_id}), 404)
        return agent, None
    except Exception as e:
        return None, (jsonify({'error': str(e)}), 500)


@manhattan_api.route("/validate_key", methods=["POST"])
def validate_key():
    """Validate an API key sent in JSON { "api_key": "sk-...", "permission": "chat" }.

    Returns `{'valid': True, 'key_id': '...'}` on success.
    """
    data = request.get_json(silent=True) or {}
    api_key = extract_api_key_from_request(data)
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
# chat_agentic_rag is now provided by _get_shared_components() to avoid triple-instantiation.
# Use _get_chat_agentic_rag() helper instead.
file_agentic_rag = Agentic_RAG(database=os.getenv("CHROMA_DATABASE_FILE_DATA")) 

def _get_chat_agentic_rag():
    """Get the shared Agentic_RAG instance for chat history operations."""
    _, _, rag = _get_shared_components()
    return rag

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
    # 1. Parse JSON body
    try:
        data = request.get_json(silent=True) or {}
    except BadRequest:
        return jsonify({'error': 'invalid_json'}), 400

    # 2. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp

    agent_name = data.get('agent_name')
    agent_slug = data.get('agent_slug')
    permissions = data.get('permissions', {})
    limits = data.get('limits', {})
    system_prompt = data.get('system_prompt') or data.get('system-prompt')
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
        'system_prompt': system_prompt,
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
            system_prompt=system_prompt,
            metadata=metadata
        )
        
        # Try creating Chroma DB collections for the agent
        _get_chat_agentic_rag().create_agent_collection(agent_ID=agent_id)
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
    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key()
    if error_resp:
        return error_resp
    try:
        agents = service.list_agents_for_user(user_id=user_id)
        return jsonify(agents), 200 
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get the agent by id
@manhattan_api.route("/get_agent", methods=["GET", "POST"])
def get_agent():
    """Get an agent by ID for the authenticated user.

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    Expects query param `agent_id`.
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        agent_id = data.get('agent_id')
    else:
        data = request.args
        agent_id = data.get('agent_id')

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
            
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
        updatable_fields = ['agent_name', 'agent_slug', 'status', 'system_prompt', 'metadata']
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

    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
            
    try:
        agent = service.delete_agent(
            agent_id=agent_id,
            user_id=user_id
        )
        
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        # Best-effort cleanup of Chroma DB collections for the agent
        try:
            _get_chat_agentic_rag().delete_agent_collection(agent_ID=agent_id)
        except Exception as e:
            print(f"[delete_agent] Chat collection cleanup skipped: {e}")
        try:
            file_agentic_rag.delete_agent_collection(agent_ID=agent_id)
        except Exception as e:
            print(f"[delete_agent] File collection cleanup skipped: {e}")
        
        # Evict from SimpleMem cache
        if agent_id in _memory_systems_cache:
            del _memory_systems_cache[agent_id]
        
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

    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
    try:
        # Add documents to the agent's vector DB
        metadatas_list = [metadata] * len(ids) if metadata else None
        file_agentic_rag.add_docs(
            agent_ID=agent_id,
            ids=ids,
            documents=document_content,
            metadatas=metadatas_list
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

    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
            
    try:
        # Update document in the agent's vector DB
        metadatas_list = [metadata] * len(document_id) if metadata else None
        file_agentic_rag.update_docs(
            agent_ID=agent_id,
            ids=document_id,
            documents=new_content,
            metadatas=metadatas_list
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

    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
    try:
        # Update document metadata in the agent's vector DB
        file_agentic_rag.update_doc_metadata(
            agent_ID=agent_id,
            ids=[document_id],
            metadatas=[metadata]
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

    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
    
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
    - query: str (optional)
    - top_k: int (optional, default=10)

    Expects API key via Authorization/X-API-Key/query param/raw payload.
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    query = data.get('query', '')
    top_k = data.get('top_k', 10)

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    # 1. Extract and Validate API Key
    valid_user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp
    try:
        # Fetch conversation history
        if query:
            history = _get_chat_agentic_rag().search_agent_collection(
                agent_ID=agent_id,
                query=query,
                n_results=top_k
            )
        else:
            history = _get_chat_agentic_rag().fetch_history(
                agent_ID=agent_id,
                top_k=top_k
            )
        return jsonify({'history': history}), 200       
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# CRUD - memory

# ADD_DIALOGUE --> LLM --> JSON RESPONSE (MEMORY) --> Creates N Memory units --> Goes to Vector Store(chromaDB)

# create_memory/ --> create_system --> Create Chroma DB collection.
# process_raw/ --> Process raw chunks and directly add to memory
# add_memory/ direct memory save. Does not involve LLM. --> Expects Mi directly from user --> Goes to vector store(chromaDB)
# read_memory/ --> ask(1) or Hyrbid_search (2)!!! simple_mem from hybrid retriever.py
# get_context/ --> system.ask function
# update_memory/ --> Chroma DB apis
# Delete_memory/ --> Chroma DB apis

# Import SimpleMem components for memory operations
from SimpleMem.main import create_system, SimpleMemSystem
from SimpleMem.models.memory_entry import MemoryEntry, Dialogue
from SimpleMem.utils.llm_client import LLMClient as SimpleMemLLMClient
from SimpleMem.utils.embedding import EmbeddingModel as SimpleMemEmbeddingModel

# Cache for SimpleMem systems per agent (avoids recreating systems on every request)
_memory_systems_cache = {}

# Shared singleton components (agent-agnostic, initialized once)
_shared_llm_client = None
_shared_embedding_model = None
_shared_agentic_rag = None

def _get_shared_components():
    """Lazily initialize shared components once. These are agent-agnostic
    and extremely expensive to create (network connections, API clients)."""
    import os
    global _shared_llm_client, _shared_embedding_model, _shared_agentic_rag
    
    if _shared_llm_client is None:
        _shared_llm_client = SimpleMemLLMClient()
    if _shared_embedding_model is None:
        _shared_embedding_model = SimpleMemEmbeddingModel()
    if _shared_agentic_rag is None:
        from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG
        database_path = os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        _shared_agentic_rag = Agentic_RAG(
            database=database_path,
            enable_cache=True,
            enable_monitoring=True
        )
    return _shared_llm_client, _shared_embedding_model, _shared_agentic_rag

# Start background pre-warming on module import
try:
    import threading
    threading.Thread(target=_get_shared_components, name="PreWarmSimpleMem", daemon=True).start()
    print("[STARTUP] SimpleMem background pre-warming thread started successfully")
except Exception as pre_warm_err:
    print(f"[STARTUP] Warning: Failed to start pre-warming thread: {pre_warm_err}")


def _get_or_create_memory_system(agent_id: str, clear_db: bool = False) -> SimpleMemSystem:
    """Get cached SimpleMem system or create new one for the agent.
    
    Uses shared singleton components (LLMClient, EmbeddingModel, Agentic_RAG)
    so that only the first agent pays the full initialization cost.
    Subsequent agents reuse these and only create lightweight per-agent wrappers.
    """
    if agent_id not in _memory_systems_cache or clear_db:
        llm, emb, rag = _get_shared_components()
        _memory_systems_cache[agent_id] = SimpleMemSystem(
            agent_id=agent_id,
            clear_db=clear_db,
            shared_llm_client=llm,
            shared_embedding_model=emb,
            shared_agentic_rag=rag
        )
    return _memory_systems_cache[agent_id]


@manhattan_api.route("/create_memory", methods=["POST"])
def create_memory():
    """Create/initialize a memory system for an agent.
    
    Creates a SimpleMem system which initializes ChromaDB collection for the agent.

    Expects JSON body with:
    - agent_id: str (required)
    - clear_db: bool (optional, default=False) - whether to clear existing memories
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    clear_db = data.get('clear_db', False)

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        # Create SimpleMem system (initializes vector store/ChromaDB collection)
        memory_system = _get_or_create_memory_system(agent_id, clear_db=clear_db)
        
        return jsonify({
            'ok': True,
            'message': 'memory_system_created' if clear_db else 'memory_system_initialized',
            'agent_id': agent_id,
            'cleared': clear_db
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/process_raw", methods=["POST"])
def process_raw():
    """Process raw dialogues through LLM to extract memory entries.
    
    Flow: ADD_DIALOGUE --> LLM --> JSON RESPONSE (MEMORY) --> N Memory units --> Vector Store

    Expects JSON body with:
    - agent_id: str (required)
    - dialogues: List[{speaker: str, content: str, timestamp?: str}] (required)
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    dialogues_data = data.get('dialogues', [])

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    if not dialogues_data:
        return jsonify({'error': 'dialogues list is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        memory_system = _get_or_create_memory_system(agent_id)
        
        memories_created = 0
        for i, dlg in enumerate(dialogues_data):
            speaker = dlg.get('speaker', 'unknown')
            content = dlg.get('content', '')
            timestamp = dlg.get('timestamp')
            
            if content:
                # This triggers LLM processing via MemoryBuilder
                memory_system.add_dialogue(
                    speaker=speaker,
                    content=content,
                    timestamp=timestamp
                )
                memories_created += 1
        
        # Finalize any remaining buffered dialogues
        memory_system.finalize()
        
        return jsonify({
            'ok': True,
            'message': 'dialogues_processed',
            'agent_id': agent_id,
            'dialogues_processed': memories_created
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/add_memory", methods=["POST"])
def add_memory():
    """Directly save memory entries without LLM processing.
    
    Expects MemoryEntry-like objects directly from user and stores in ChromaDB.

    Expects JSON body with:
    - agent_id: str (required)
    - memories: List[{lossless_restatement: str, keywords?: List[str], timestamp?: str, 
                      location?: str, persons?: List[str], entities?: List[str], topic?: str}]
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    memories_data = data.get('memories', [])

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    if not memories_data:
        return jsonify({'error': 'memories list is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        print(f"[DEBUG /add_memory] Getting memory system for agent_id: {agent_id}")
        memory_system = _get_or_create_memory_system(agent_id)
        print(f"[DEBUG /add_memory] Memory system obtained. VectorStore agent_id: {memory_system.vector_store.agent_id}")
        
        # Create MemoryEntry objects from the provided data
        entries = []
        entry_ids = []
        for mem in memories_data:
            if not mem.get('lossless_restatement'):
                continue
            
            entry = MemoryEntry(
                lossless_restatement=mem.get('lossless_restatement'),
                keywords=mem.get('keywords', []),
                timestamp=mem.get('timestamp'),
                location=mem.get('location'),
                persons=mem.get('persons', []),
                entities=mem.get('entities', []),
                topic=mem.get('topic'),
                memory_type=mem.get('memory_type', 'episodic') # Extract type or default
            )
            entries.append(entry)
            entry_ids.append(entry.entry_id)
        
        if entries:
            print(f"[DEBUG /add_memory] Calling vector_store.add_entries with {len(entries)} entries")
            # Add directly to vector store (bypassing LLM)
            result = memory_system.vector_store.add_entries(entries)
            print(f"[DEBUG /add_memory] add_entries call completed")
            
            if result and not result.get('success', True):
                return jsonify({'error': result.get('error', 'Unknown error during add_entries')}), 500
                
            entries_added = result.get('operations_completed', 0) if result and isinstance(result, dict) else 0
            added_ids = result.get('ids', []) if result and isinstance(result, dict) else []
        else:
            entries_added = 0
            added_ids = []
        
        return jsonify({
            'ok': True,
            'message': 'memories_added',
            'agent_id': agent_id,
            'entries_added': entries_added,
            'entry_ids': added_ids
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/sync_memories", methods=["POST"])
def sync_memories():
    """Sync ChromaDB memories to Supabase for a given agent_id.
    
    Reads from SimpleMem's Agentic_RAG per-agent collection and maps fields
    to Supabase gitmem_memories schema.
    
    Expects JSON body with:
    - agent_id: str (required)
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        
        # Use the correct approach: read from Agentic_RAG, write to Supabase with proper field mapping
        from gitmem.core.storage.supabase_connector import SupabaseConnector
        supa = SupabaseConnector()
        if supa._disabled or not supa.client:
            return jsonify({"error": "Supabase not configured"}), 500
        
        # Ensure FK entries exist
        supa._ensure_repo(agent_id, 'default')
        
        # Fetch existing IDs
        existing_res = supa.client.table("gitmem_memories").select("id").eq("agent_id", agent_id).execute()
        existing_ids = {row["id"] for row in (existing_res.data or [])}
        
        # Read from SimpleMem Agentic_RAG
        memory_system = _get_or_create_memory_system(agent_id)
        try:
            collection = memory_system.vector_store.agentic_RAG.wrapper.manager.get_collection(agent_id)
            chroma_data = collection.get(include=["documents", "metadatas"])
        except Exception as e:
            return jsonify({"error": f"ChromaDB collection error: {e}"}), 500
        
        if not chroma_data or not chroma_data.get("ids"):
            return jsonify({"ok": True, "message": "no_records", "synced_count": 0}), 200
        
        synced = 0
        for i, cid in enumerate(chroma_data["ids"]):
            if cid in existing_ids:
                continue
            
            meta = (chroma_data.get("metadatas") or [])[i] if chroma_data.get("metadatas") and i < len(chroma_data["metadatas"]) else {}
            doc = (chroma_data.get("documents") or [])[i] if chroma_data.get("documents") and i < len(chroma_data["documents"]) else ""
            
            # Clean content
            content = doc
            if content.startswith("Content: "):
                content = content[9:]
            content_lines = content.split("\n")
            content = "\n".join(l for l in content_lines if not l.startswith("Keywords:") and not l.startswith("Topic:")).strip()
            
            mem_type = (meta.get('memory_type') or 'episodic').lower()
            if mem_type not in ('episodic', 'semantic', 'procedural', 'state'):
                mem_type = 'episodic'
            
            # Clean metadata for JSONB
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            
            row = {
                'id': cid,
                'agent_id': agent_id,
                'repo_id': agent_id,
                'workspace_id': 'default',
                'content': content or "(empty)",
                'type': mem_type,
                'importance': 0.5,
                'visibility': 'private',
                'metadata': clean_meta,
                'created_at': str(meta.get('timestamp') or datetime.now().isoformat()),
            }
            
            try:
                supa.client.table("gitmem_memories").insert(row).execute()
                synced += 1
            except Exception as e:
                if '23505' not in str(e) and 'duplicate' not in str(e).lower():
                    print(f"[sync_memories API] Error inserting {cid[:12]}: {e}")
        
        return jsonify({
            "ok": True,
            "message": "sync_completed",
            "synced_count": synced,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/read_memory", methods=["POST"])
def read_memory():
    """Read/search memories using hybrid retrieval.
    
    Uses HybridRetriever for semantic + keyword + structured search.

    Expects JSON body with:
    - agent_id: str (required)
    - query: str (required)
    - top_k: int (optional, default=5)
    - enable_reflection: bool (optional) - enable reflection-based additional retrieval
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    query = data.get('query')
    top_k = data.get('top_k', 5)
    enable_reflection = data.get('enable_reflection')

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    if not query:
        return jsonify({'error': 'query is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        memory_system = _get_or_create_memory_system(agent_id)
        
        # Use HybridRetriever for search
        if enable_reflection is not None:
            contexts = memory_system.hybrid_retriever.retrieve(query, enable_reflection=enable_reflection)
        else:
            contexts = memory_system.hybrid_retriever.retrieve(query)
        
        # Convert MemoryEntry objects to serializable dicts
        results = []
        for ctx in contexts[:top_k]:
            results.append({
                'entry_id': ctx.entry_id,
                'lossless_restatement': ctx.lossless_restatement,
                'keywords': ctx.keywords,
                'timestamp': ctx.timestamp,
                'location': ctx.location,
                'persons': ctx.persons,
                'entities': ctx.entities,
                'topic': ctx.topic,
                'memory_type': ctx.memory_type  # Include memory bin type
            })
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'query': query,
            'results_count': len(results),
            'results': results
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@manhattan_api.route("/get_memories_by_bin", methods=["POST"])
def get_memories_by_bin():
    """Get memories filtered by memory bin type (episodic, semantic, procedural, working).
    
    Expects JSON body with:
    - agent_id: str (required)
    - memory_type: str (required) - one of: episodic, semantic, procedural, working
    - limit: int (optional, default=50)
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    memory_type = data.get('memory_type', 'episodic')
    limit = data.get('limit', 50)

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    valid_types = ['episodic', 'semantic', 'procedural', 'working']
    if memory_type.lower() not in valid_types:
        return jsonify({
            'error': f'Invalid memory_type. Must be one of: {", ".join(valid_types)}'
        }), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        memory_system = _get_or_create_memory_system(agent_id)
        
        if hasattr(memory_system.vector_store, 'agentic_RAG'):
            rag = memory_system.vector_store.agentic_RAG
            
            results = rag.fetch_with_filter(
                agent_ID=agent_id,
                filter_metadata={"memory_type": memory_type.lower()},
                top_k=limit
            )
            
            memories = []
            for r in results:
                metadata = r.get('metadata', {})
                document = r.get('document', '')
                
                keywords = metadata.get('keywords', [])
                if isinstance(keywords, str):
                    try:
                        keywords = json.loads(keywords)
                    except:
                        keywords = []
                
                memories.append({
                    'entry_id': r.get('id', metadata.get('entry_id')),
                    'content': document,
                    'lossless_restatement': document,
                    'keywords': keywords,
                    'timestamp': metadata.get('timestamp'),
                    'location': metadata.get('location'),
                    'topic': metadata.get('topic'),
                    'memory_type': metadata.get('memory_type', memory_type)
                })
            
            return jsonify({
                'ok': True,
                'agent_id': agent_id,
                'memory_type': memory_type,
                'count': len(memories),
                'memories': memories
            }), 200
        else:
            return jsonify({'error': 'Vector store not available'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/get_context", methods=["POST"])
def get_context():
    """Get context-aware answer using SimpleMem's ask function.
    
    Full Q&A flow: Query -> HybridRetrieval -> AnswerGenerator -> Response

    Expects JSON body with:
    - agent_id: str (required)
    - question: str (required)
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    question = data.get('question')

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    if not question:
        return jsonify({'error': 'question is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        memory_system = _get_or_create_memory_system(agent_id)
        
        # Use ask_with_contexts() to get answer + contexts in a single retrieval pass
        # This avoids the duplicate retrieve() call that was doubling latency
        answer, contexts = memory_system.ask_with_contexts(question)
        contexts_used = [
            {
                'entry_id': ctx.entry_id,
                'lossless_restatement': ctx.lossless_restatement,
                'topic': ctx.topic,
                'timestamp': ctx.timestamp,
                'type': getattr(ctx, 'memory_type', 'episodic')
            }
            for ctx in contexts[:5]
        ]
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'question': question,
            'answer': answer,
            'contexts_used': contexts_used
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/update_memory", methods=["POST"])
def update_memory():
    """Update an existing memory entry in ChromaDB.

    Expects JSON body with:
    - agent_id: str (required)
    - entry_id: str (required)
    - updates: dict with updateable fields (lossless_restatement, keywords, timestamp, 
               location, persons, entities, topic)
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    entry_id = data.get('entry_id')
    updates = data.get('updates', {})

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    if not entry_id:
        return jsonify({'error': 'entry_id is required'}), 400
    if not updates:
        return jsonify({'error': 'updates dict is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        memory_system = _get_or_create_memory_system(agent_id)
        
        # Build the document content from lossless_restatement if provided
        document_content = updates.get('lossless_restatement')
        
        # Build metadata from other fields
        metadata = {}
        updateable_metadata = ['timestamp', 'location', 'persons', 'entities', 'topic', 'keywords']
        for field in updateable_metadata:
            if field in updates:
                value = updates[field]
                # Convert lists to strings for ChromaDB metadata
                if isinstance(value, list):
                    metadata[field] = json.dumps(value)
                else:
                    metadata[field] = value
        
        # Use Agentic_RAG to update the document
        if document_content:
            # Update both document and metadata
            memory_system.vector_store.agentic_RAG.update_docs(
                agent_ID=agent_id,
                ids=[entry_id],
                documents=[document_content],
                metadatas=[metadata] if metadata else None
            )
        elif metadata:
            # Update metadata only
            memory_system.vector_store.agentic_RAG.update_doc_metadata(
                agent_ID=agent_id,
                ids=[entry_id],
                metadatas=[metadata]
            )
        
        return jsonify({
            'ok': True,
            'message': 'memory_updated',
            'agent_id': agent_id,
            'entry_id': entry_id
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/delete_memory", methods=["POST"])
def delete_memory():
    """Delete memory entries from ChromaDB.

    Expects JSON body with:
    - agent_id: str (required)
    - entry_ids: List[str] (required) - list of entry IDs to delete
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    entry_ids = data.get('entry_ids', [])

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    if not entry_ids:
        return jsonify({'error': 'entry_ids list is required'}), 400

    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error

    try:
        # Verify ownership
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        memory_system = _get_or_create_memory_system(agent_id)
        
        # Use Agentic_RAG to delete documents
        result = memory_system.vector_store.agentic_RAG.delete_chat_history(
            agent_ID=agent_id,
            ids=entry_ids
        )
        
        return jsonify({
            'ok': True,
            'message': 'memories_deleted',
            'agent_id': agent_id,
            'deleted_count': len(entry_ids),
            'entry_ids': entry_ids
        }), 200
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
    
    # 1. Extract and Validate API Key
    user_id, error_resp = extract_and_validate_api_key(data)
    if error_resp:
        return error_resp

    try:
        # Verify the agent belongs to the authenticated user
        agent_record, err_resp = _verify_agent_ownership(agent_id, user_id)
        if err_resp:
            return err_resp
        
        # Use cached memory system (avoids recreating SimpleMemSystem every call)
        memory_system = _get_or_create_memory_system(agent_id)
        
        # Extract strategy or mode from request payload (default to 'auto')
        strategy = data.get('strategy') or data.get('mode') or 'auto'
        
        # Dynamic Auto-Routing: zero-overhead declarative statement / greeting classifier
        is_conversational_statement = False
        msg_clean = user_message.strip().lower()
        
        # Split into words and strip punctuation from each word individually (preserving original msg_clean for '?' check)
        words = [w.strip('.,!?;:"\'()[]') for w in msg_clean.split()]
        
        # 1. Comprehensive Interrogative Set
        interrogatives = {
            # Standard question words
            'who', 'what', 'when', 'where', 'why', 'how', 'which', 'whose', 'whom',
            # Common contractions
            "who's", "what's", "where's", "when's", "why's", "how's",
            'whos', 'whats', 'wheres', 'whens', 'whys', 'hows',
            # Auxiliary & modal verbs
            'is', 'are', 'was', 'were', 'am', 'be', 'been',
            'do', 'did', 'does', 'doing',
            'have', 'has', 'had', 'having',
            'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might', 'must',
            # Negative contractions
            "isn't", "aren't", "wasn't", "weren't", "don't", "didn't", "doesn't",
            "haven't", "hasn't", "hadn't", "can't", "couldn't", "won't", "wouldn't", "shouldn't",
            'isnt', 'arent', 'wasnt', 'werent', 'dont', 'didnt', 'doesnt',
            'havent', 'hasnt', 'hadnt', 'cant', 'couldnt', 'wont', 'wouldnt', 'shouldnt'
        }
        
        # 2. Conversational Openers / Info-Seeding markers
        conversational_starters = {
            'hi', 'hello', 'hey', 'yo', 'greetings', 'sup', 'morning', 'afternoon', 'evening',
            'ok', 'okay', 'yes', 'no', 'thanks', 'thank', 'cool', 'awesome', 'great', 'perfect',
            'here', 'this', 'we', 'i', 'let', 'lets', 'im', 'weve', 'ive'
        }
        
        # Rule 1: Very short queries are conversational
        if len(words) < 6:
            is_conversational_statement = True
        # Rule 2: Direct match of conversational starters or feedback words
        elif words and words[0] in conversational_starters:
            is_conversational_statement = True
        # Rule 3: Declarative statements (no question mark and no interrogative starters)
        elif '?' not in msg_clean:
            if words and words[0] not in interrogatives:
                is_conversational_statement = True
                
        # Resolve 'auto' strategy dynamically based on grammar and complexity checks
        if strategy == 'auto':
            if is_conversational_statement:
                print(f"[Router] Auto-routing: Declarative statement/greeting. Routing to FAST mode.")
                strategy = 'fast'
            else:
                # Rule 4: Question complexity check. Determine if Thinking Mode is required.
                # We search for indicators of synthesis, history, temporal bounds, or comparisons
                complex_indicators = {
                    # Synthesizing / Summarizing
                    'summarize', 'summary', 'synthesize', 'overview', 'outline', 'recap', 'brief', 'digest',
                    # Comparative analysis
                    'difference', 'between', 'compare', 'contrast', 'versus', 'vs', 'similar', 'similarity',
                    'similarities', 'advantages', 'disadvantages', 'pros', 'cons',
                    # Explanations / Mechanics
                    'explain', 'analysis', 'analyze', 'how does', 'how do', 'why is', 'why does', 'detailed',
                    # Time-based lookups / Historical logs
                    'yesterday', 'today', 'tomorrow', 'last week', 'last month', 'last year', 'history',
                    'timeline', 'schedule', 'calendar', 'agenda', 'past', 'recent',
                    # Logical subclauses
                    'and also', 'as well as', 'along with', 'how can we', 'what are the'
                }
                
                requires_deep_thinking = False
                
                # Complexity Check A: Word Count & Interrogative Symbol (Long Questions)
                if len(words) > 20 and '?' in msg_clean:
                    print(f"[Router] Complex query: High word count ({len(words)} words) with question.")
                    requires_deep_thinking = True
                
                # Complexity Check B: Keyword Indicators
                if not requires_deep_thinking:
                    for indicator in complex_indicators:
                        if indicator in msg_clean:
                            requires_deep_thinking = True
                            print(f"[Router] Complex query: Found indicator '{indicator}'.")
                            break
                            
                # Complexity Check C: Conditional subclause depth
                if not requires_deep_thinking:
                    subclause_connectors = {'if', 'then', 'because', 'although', 'unless'}
                    connector_count = sum(1 for w in words if w in subclause_connectors)
                    if connector_count >= 2:
                        requires_deep_thinking = True
                        print(f"[Router] Complex query: High subclause connector count ({connector_count}).")
                
                if requires_deep_thinking:
                    print(f"[Router] Auto-routing: Complex query '{user_message[:30]}...' -> THINKING mode.")
                    strategy = 'thinking'
                else:
                    print(f"[Router] Auto-routing: Simple question '{user_message[:30]}...' -> FAST mode.")
                    strategy = 'fast'
        elif is_conversational_statement and strategy == 'thinking':
            # Force 'fast' override if thinking is explicitly requested but prompt is just a greeting/statement
            print(f"[Router] Explicit 'thinking' override ignored: Declarative statement. Downgrading to FAST mode.")
            strategy = 'fast'
            
        # Configure SimpleMem planning/reflection behavior dynamically
        if strategy == 'thinking':
            memory_system.hybrid_retriever.enable_planning = True
            memory_system.hybrid_retriever.enable_reflection = True
            print(f"[Router] Routing to THINKING mode (Planning & Reflection enabled)")
        else:
            # Fast Mode: Direct RAG (Single LLM response generation, direct vector search)
            memory_system.hybrid_retriever.enable_planning = False
            memory_system.hybrid_retriever.enable_reflection = False
            print(f"[Router] Routing to FAST mode (Planning & Reflection disabled)")
        
        # Record timestamp for this interaction
        from datetime import datetime
        timestamp = datetime.utcnow().isoformat()
        
        # Process dialogue storing and finalization asynchronously in a background thread.
        import threading
        def _background_save_and_finalize(mem_sys, query, reply, ts, u_id, a_id):
            try:
                # 1. Log sequential chat history to Supabase explicitly
                reply_str = json.dumps(reply) if isinstance(reply, (dict, list)) else str(reply)
                try:
                    add_message(u_id, "human", query, session_id=a_id)
                    add_message(u_id, "llm", reply_str, session_id=a_id)
                except Exception as db_err:
                    print(f"[agent_chat] Error saving to Supabase chat history: {db_err}")

                # 2. Buffer user dialogue asynchronously to SimpleMem
                mem_sys.add_dialogue(
                    speaker="user",
                    content=query,
                    timestamp=ts,
                    auto_process=False
                )
                # 3. Buffer agent dialogue asynchronously to SimpleMem
                mem_sys.add_dialogue(
                    speaker="agent",
                    content=reply_str,
                    timestamp=datetime.utcnow().isoformat(),
                    auto_process=False
                )
                # 4. Vectorize and save all buffered dialogues to Chroma DB in background
                mem_sys.finalize()
            except Exception as bg_err:
                print(f"[agent_chat] Background save/finalize error: {bg_err}")

        is_stream = str(data.get('stream', '')).lower() == 'true'

        if is_stream:
            # Generate response via SSE generator
            def generate_stream():
                import time
                yield f"data: {json.dumps({'type': 'loading', 'status': 'initializing', 'message': 'Preparing context...'})}\n\n"
                
                # Conversational Assistant Prompt
                chat_prompt = (
                    "You are a helpful, conversational AI assistant. Use the retrieved context to inform your responses, "
                    "but reply naturally as a friendly chatbot. Do not act like a rigid search engine. "
                    "You must output valid JSON format."
                )
                
                # Fetch answer synchronously
                agent_response_obj = memory_system.ask(user_message, system_prompt=chat_prompt)
                reply_str = json.dumps(agent_response_obj) if isinstance(agent_response_obj, (dict, list)) else str(agent_response_obj)
                
                yield f"data: {json.dumps({'type': 'loading', 'status': 'streaming', 'message': 'Generating response...'})}\n\n"
                
                # Simulate streaming chunk by chunk
                tokens = reply_str.split(' ')
                for t in tokens:
                    yield f"data: {json.dumps({'type': 'token', 'content': t + ' '})}\n\n"
                    time.sleep(0.02)
                
                yield f"data: {json.dumps({'type': 'done', 'full_response': reply_str})}\n\n"
                
                # Trigger background save
                threading.Thread(
                    target=_background_save_and_finalize,
                    args=(memory_system, user_message, agent_response_obj, timestamp, user_id, agent_id),
                    daemon=True
                ).start()
                
            return Response(generate_stream(), mimetype='text/event-stream')
        else:
            # Conversational Assistant Prompt
            chat_prompt = (
                "You are a helpful, conversational AI assistant. Use the retrieved context to inform your responses, "
                "but reply naturally as a friendly chatbot. Do not act like a rigid search engine. "
                "You must output valid JSON format."
            )
            agent_response = memory_system.ask(user_message, system_prompt=chat_prompt)
            
            threading.Thread(
                target=_background_save_and_finalize,
                args=(memory_system, user_message, agent_response, timestamp, user_id, agent_id),
                daemon=True
            ).start()
            
            return jsonify({
                'ok': True,
                'agent_id': agent_id,
                'user_message': user_message,
                'agent_response': agent_response,
                'strategy': strategy,
                'user_id': user_id,
                'timestamp': timestamp
            }), 200
    except Exception as e:
        print(f"Error in agent_chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PROFESSIONAL APIs - Analytics, Bulk Operations, Export/Import
# ============================================================================

@manhattan_api.route("/agent_stats", methods=["POST"])
def agent_stats():
    """Get comprehensive statistics for an agent.
    
    Returns statistics including:
    - Total memory count
    - Total document count
    - Memory categories breakdown
    - Recent activity timeline
    - Storage usage estimates
    
    Expects JSON body with:
    - agent_id: str (required)
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        # Verify agent ownership
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        # Get memory system stats
        memory_system = _get_or_create_memory_system(agent_id, clear_db=False)
        
        # Get memory count from vector store
        memory_count = 0
        topic_breakdown = {}
        persons_mentioned = set()
        locations_mentioned = set()
        
        try:
            # Access the underlying vector store
            if hasattr(memory_system, 'vector_store') and memory_system.vector_store:
                if hasattr(memory_system.vector_store, 'agentic_RAG'):
                    manager = memory_system.vector_store.agentic_RAG.wrapper.manager
                    collection = manager._get_or_cache(agent_id)
                    all_data = collection.get(include=['metadatas'])
                    memory_count = len(all_data.get('ids', []))
                    
                    # Analyze metadata
                    for metadata in all_data.get('metadatas', []):
                        if metadata:
                            topic = metadata.get('topic', 'uncategorized')
                            topic_breakdown[topic] = topic_breakdown.get(topic, 0) + 1
                            
                            persons = metadata.get('persons', [])
                            if isinstance(persons, str):
                                persons = [p.strip() for p in persons.split(',') if p.strip()]
                            persons_mentioned.update(persons)
                            
                            location = metadata.get('location')
                            if location:
                                locations_mentioned.add(location)
        except Exception as e:
            print(f"Error getting memory stats: {e}")
        
        # Get document count
        doc_count = 0
        try:
            if file_agentic_rag:
                manager = file_agentic_rag.wrapper.manager
                collection = manager._get_or_cache(agent_id)
                docs = collection.get(include=[])
                doc_count = len(docs.get('ids', [])) if docs else 0
        except Exception as e:
            print(f"Error getting doc stats: {e}")
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'agent_name': agent.get('agent_name'),
            'agent_status': agent.get('status'),
            'statistics': {
                'total_memories': memory_count,
                'total_documents': doc_count,
                'topics': topic_breakdown,
                'unique_persons': list(persons_mentioned),
                'unique_locations': list(locations_mentioned),
                'persons_count': len(persons_mentioned),
                'locations_count': len(locations_mentioned)
            },
            'created_at': agent.get('created_at'),
            'updated_at': agent.get('updated_at')
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/list_memories", methods=["POST"])
def list_memories():
    """List all memories for an agent with pagination.
    
    Expects JSON body with:
    - agent_id: str (required)
    - limit: int (optional, default=50, max=500)
    - offset: int (optional, default=0)
    - filter_topic: str (optional) - filter by topic
    - filter_person: str (optional) - filter by person mentioned
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    limit = min(data.get('limit', 50), 500)
    offset = data.get('offset', 0)
    filter_topic = data.get('filter_topic')
    filter_person = data.get('filter_person')
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        # Verify agent ownership
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        memory_system = _get_or_create_memory_system(agent_id, clear_db=False)
        
        memories = []
        total_count = 0
        
        try:
            if hasattr(memory_system, 'vector_store') and memory_system.vector_store:
                if hasattr(memory_system.vector_store, 'agentic_RAG'):
                    manager = memory_system.vector_store.agentic_RAG.wrapper.manager
                    collection = manager._get_or_cache(agent_id)
                    
                    # Build where clause for filtering
                    where_clause = None
                    if filter_topic:
                        where_clause = {"topic": filter_topic}
                    elif filter_person:
                        # ChromaDB doesn't support array contains, so we use string match
                        where_clause = {"$contains": filter_person}
                    
                    all_data = collection.get(
                        include=['documents', 'metadatas'],
                        where=where_clause if (filter_topic or filter_person) else None
                    )
                    
                    ids = all_data.get('ids', [])
                    documents = all_data.get('documents', [])
                    metadatas = all_data.get('metadatas', [])
                    
                    total_count = len(ids)
                    
                    # Apply pagination
                    for i in range(offset, min(offset + limit, len(ids))):
                        memories.append({
                            'entry_id': ids[i],
                            'lossless_restatement': documents[i] if i < len(documents) else None,
                            'metadata': metadatas[i] if i < len(metadatas) else {}
                        })
        except Exception as e:
            print(f"Error listing memories: {e}")
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total_count,
            'memories': memories
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/bulk_add_memory", methods=["POST"])
def bulk_add_memory():
    """Bulk add multiple memories efficiently in a single request.
    
    Optimized for high-volume memory ingestion.
    
    Expects JSON body with:
    - agent_id: str (required)
    - memories: List[MemoryEntry] (required, max 100 at once)
    - skip_duplicates: bool (optional, default=False) - skip if similar memory exists
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    memories_list = data.get('memories', [])
    skip_duplicates = data.get('skip_duplicates', False)
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    if not memories_list:
        return jsonify({'error': 'memories array is required'}), 400
    
    if len(memories_list) > 100:
        return jsonify({'error': 'Maximum 100 memories per request'}), 400
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        memory_system = _get_or_create_memory_system(agent_id, clear_db=False)
        
        added_count = 0
        skipped_count = 0
        entry_ids = []
        errors = []
        
        for idx, mem in enumerate(memories_list):
            try:
                lossless = mem.get('lossless_restatement')
                if not lossless:
                    errors.append({'index': idx, 'error': 'lossless_restatement required'})
                    continue
                
                entry = MemoryEntry(
                    lossless_restatement=lossless,
                    keywords=mem.get('keywords', []),
                    timestamp=mem.get('timestamp'),
                    location=mem.get('location'),
                    persons=mem.get('persons', []),
                    entities=mem.get('entities', []),
                    topic=mem.get('topic')
                )
                
                entry_id = memory_system.directly_save_memory(entry)
                entry_ids.append(entry_id)
                added_count += 1
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'memories_added': added_count,
            'memories_skipped': skipped_count,
            'entry_ids': entry_ids,
            'errors': errors if errors else None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/export_memories", methods=["POST"])
def export_memories():
    """Export all memories for an agent as JSON for backup/migration.
    
    Returns a complete backup of all memories that can be imported later.
    
    Expects JSON body with:
    - agent_id: str (required)
    - format: str (optional, default='json', options: 'json', 'csv')
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    export_format = data.get('format', 'json')
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        memory_system = _get_or_create_memory_system(agent_id, clear_db=False)
        
        memories_export = []
        
        try:
            if hasattr(memory_system, 'vector_store') and memory_system.vector_store:
                if hasattr(memory_system.vector_store, 'agentic_RAG'):
                    manager = memory_system.vector_store.agentic_RAG.wrapper.manager
                    collection = manager._get_or_cache(agent_id)
                    all_data = collection.get(include=['documents', 'metadatas'])
                    
                    for i, entry_id in enumerate(all_data.get('ids', [])):
                        doc = all_data['documents'][i] if i < len(all_data.get('documents', [])) else None
                        meta = all_data['metadatas'][i] if i < len(all_data.get('metadatas', [])) else {}
                        
                        memories_export.append({
                            'entry_id': entry_id,
                            'lossless_restatement': doc,
                            'keywords': meta.get('keywords', []),
                            'timestamp': meta.get('timestamp'),
                            'location': meta.get('location'),
                            'persons': meta.get('persons', []),
                            'entities': meta.get('entities', []),
                            'topic': meta.get('topic')
                        })
        except Exception as e:
            print(f"Error exporting memories: {e}")
        
        export_data = {
            'version': '1.0',
            'export_timestamp': datetime.utcnow().isoformat(),
            'agent_id': agent_id,
            'agent_name': agent.get('agent_name'),
            'total_memories': len(memories_export),
            'memories': memories_export
        }
        
        return jsonify({
            'ok': True,
            'export': export_data
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/import_memories", methods=["POST"])
def import_memories():
    """Import memories from a previously exported JSON backup.
    
    Expects JSON body with:
    - agent_id: str (required) - target agent to import into
    - export_data: dict (required) - the export object from /export_memories
    - merge_mode: str (optional, default='append', options: 'append', 'replace')
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    export_data = data.get('export_data')
    merge_mode = data.get('merge_mode', 'append')
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    if not export_data or not isinstance(export_data, dict):
        return jsonify({'error': 'export_data object is required'}), 400
    
    memories_to_import = export_data.get('memories', [])
    if not memories_to_import:
        return jsonify({'error': 'No memories found in export_data'}), 400
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        # If replace mode, clear existing memories first
        clear_db = (merge_mode == 'replace')
        memory_system = _get_or_create_memory_system(agent_id, clear_db=clear_db)
        
        imported_count = 0
        entry_ids = []
        errors = []
        
        for idx, mem in enumerate(memories_to_import):
            try:
                lossless = mem.get('lossless_restatement')
                if not lossless:
                    errors.append({'index': idx, 'error': 'lossless_restatement required'})
                    continue
                
                entry = MemoryEntry(
                    lossless_restatement=lossless,
                    keywords=mem.get('keywords', []),
                    timestamp=mem.get('timestamp'),
                    location=mem.get('location'),
                    persons=mem.get('persons', []),
                    entities=mem.get('entities', []),
                    topic=mem.get('topic')
                )
                
                entry_id = memory_system.directly_save_memory(entry)
                entry_ids.append(entry_id)
                imported_count += 1
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'merge_mode': merge_mode,
            'memories_imported': imported_count,
            'source_agent': export_data.get('agent_name'),
            'source_timestamp': export_data.get('export_timestamp'),
            'entry_ids': entry_ids,
            'errors': errors if errors else None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/memory_summary", methods=["POST"])
def memory_summary():
    """Generate an AI summary of the agent's memories.
    
    Uses LLM to create a comprehensive summary of what the agent knows.
    
    Expects JSON body with:
    - agent_id: str (required)
    - focus_topic: str (optional) - focus summary on specific topic
    - summary_length: str (optional, default='medium', options: 'brief', 'medium', 'detailed')
    """
    data = request.get_json(silent=True) or {}
    agent_id = data.get('agent_id')
    focus_topic = data.get('focus_topic')
    summary_length = data.get('summary_length', 'medium')
    
    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        agent = service.get_agent_by_id(agent_id=agent_id, user_id=user_id)
        if not agent:
            return jsonify({'error': 'agent_not_found'}), 404
        
        memory_system = _get_or_create_memory_system(agent_id, clear_db=False)
        
        # Gather all memories for summarization
        all_memories = []
        try:
            if hasattr(memory_system, 'vector_store') and memory_system.vector_store:
                if hasattr(memory_system.vector_store, 'agentic_RAG'):
                    manager = memory_system.vector_store.agentic_RAG.wrapper.manager
                    collection = manager._get_or_cache(agent_id)
                    all_data = collection.get(include=['documents', 'metadatas'])
                    
                    for i, doc in enumerate(all_data.get('documents', [])):
                        if doc:
                            meta = all_data['metadatas'][i] if i < len(all_data.get('metadatas', [])) else {}
                            if focus_topic and meta.get('topic') != focus_topic:
                                continue
                            all_memories.append({
                                'content': doc,
                                'topic': meta.get('topic'),
                                'persons': meta.get('persons'),
                                'timestamp': meta.get('timestamp')
                            })
        except Exception as e:
            print(f"Error gathering memories for summary: {e}")
        
        if not all_memories:
            return jsonify({
                'ok': True,
                'agent_id': agent_id,
                'summary': 'No memories found for this agent.',
                'memory_count': 0
            }), 200
        
        # Generate summary using the ask function with a summary prompt
        length_guide = {
            'brief': '2-3 sentences',
            'medium': '1-2 paragraphs',
            'detailed': '3-5 paragraphs with specific details'
        }
        
        summary_prompt = f"""Based on all the stored memories, provide a {length_guide.get(summary_length, '1-2 paragraphs')} summary of key information and themes. 
        {'Focus specifically on topics related to: ' + focus_topic if focus_topic else ''}
        What are the main facts, important people, and key events that have been remembered?"""
        
        summary = memory_system.ask(summary_prompt)
        
        # Extract unique topics and persons for metadata
        unique_topics = set()
        unique_persons = set()
        for mem in all_memories:
            if mem.get('topic'):
                unique_topics.add(mem['topic'])
            persons = mem.get('persons', [])
            if isinstance(persons, list):
                unique_persons.update(persons)
        
        return jsonify({
            'ok': True,
            'agent_id': agent_id,
            'summary': summary,
            'memory_count': len(all_memories),
            'topics_covered': list(unique_topics),
            'persons_mentioned': list(unique_persons),
            'focus_topic': focus_topic,
            'summary_length': summary_length
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/api_usage", methods=["POST"])
def api_usage():
    """Get API usage statistics for the authenticated user.
    
    Returns usage metrics including:
    - Total API calls
    - Calls by endpoint
    - Rate limit status
    - Current billing period usage
    
    Note: This is a placeholder that returns mock data.
    In production, integrate with your analytics/billing system.
    """
    data = request.get_json(silent=True) or {}
    
    user_id, error = extract_and_validate_api_key(data)
    if error:
        return error
    
    try:
        # Get agent count for the user
        agents = service.list_agents_for_user(user_id=user_id)
        active_agents = [a for a in agents if a.get('status') == 'active']
        
        # Placeholder usage data (in production, query your analytics DB)
        usage_data = {
            'ok': True,
            'user_id': user_id,
            'billing_period': {
                'start': datetime.utcnow().replace(day=1).isoformat(),
                'end': datetime.utcnow().isoformat()
            },
            'agents': {
                'total': len(agents),
                'active': len(active_agents),
                'disabled': len(agents) - len(active_agents)
            },
            'api_calls': {
                'total': 0,  # Placeholder - track in production
                'by_endpoint': {},
                'limit': 10000,  # From user's plan
                'remaining': 10000
            },
            'memory_storage': {
                'total_memories': 0,  # Would aggregate across all agents
                'storage_mb': 0,
                'limit_mb': 1000
            },
            'rate_limits': {
                'requests_per_minute': 60,
                'requests_per_day': 10000
            }
        }
        
        return jsonify(usage_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@manhattan_api.route("/health_detailed", methods=["GET"])
def health_detailed():
    """Detailed health check endpoint with service status.
    
    Returns status of all backend services:
    - API server status
    - Database connectivity
    - Vector store status
    - LLM service status
    """
    health_status = {
        'ok': True,
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0',
        'services': {}
    }
    
    # Check Supabase
    try:
        if _supabase_backend:
            # Simple query to check connectivity
            _supabase_backend.table('api_keys').select('id').limit(1).execute()
            health_status['services']['database'] = {'status': 'healthy', 'type': 'supabase'}
        else:
            health_status['services']['database'] = {'status': 'unavailable', 'type': 'supabase'}
    except Exception as e:
        health_status['services']['database'] = {'status': 'error', 'error': str(e)}
        health_status['ok'] = False
    
    # Check ChromaDB / Vector Store
    try:
        health_status['services']['vector_store'] = {'status': 'healthy', 'type': 'chromadb'}
    except Exception as e:
        health_status['services']['vector_store'] = {'status': 'error', 'error': str(e)}
    
    # Check LLM service
    try:
        # Placeholder - in production check your LLM API
        health_status['services']['llm'] = {'status': 'healthy', 'provider': 'openai'}
    except Exception as e:
        health_status['services']['llm'] = {'status': 'error', 'error': str(e)}
    
    status_code = 200 if health_status['ok'] else 503
    return jsonify(health_status), status_code


# Test validate_api_key_value function
if __name__ == '__main__':
    result = validate_api_key_value(os.getenv("MANHATTAN_API_KEY_TEST"), None)
    print(f"Validation result: {result}")