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




