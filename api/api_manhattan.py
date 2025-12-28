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

from flask import Blueprint, jsonify
from datetime import datetime


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

# API authentication helpers and endpoints
import os
import json
from supabase import create_client
from key_utils import hash_key, parse_json_field
from functools import wraps
from flask import request, g

# Create a server-side supabase client (service role) for validation and lookups
_SUPABASE_URL = os.environ.get('SUPABASE_URL')
_SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
try:
    _supabase_backend = create_client(_SUPABASE_URL, _SUPABASE_SERVICE_ROLE_KEY)
except Exception:
    _supabase_backend = None


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