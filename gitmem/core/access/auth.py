"""
GitMem v2.0 — Authentication Service

Validates JWT tokens and API keys to identify the Actor (user or agent).
Integrates with the Command Handler for initial request validation.
"""

from typing import Dict, Any, Optional, Tuple


class AuthService:
    """Handles authentication of users and agents."""
    
    def __init__(self, supabase_client):
        self.client = supabase_client

    def authenticate_request(self, headers: Dict[str, str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Authenticates a request based on headers.
        Returns: (is_authenticated, actor_id, auth_type)
        auth_type is either "user" or "agent"
        """
        # 1. Check for API Key (Agent/Server access)
        api_key = headers.get("X-API-Key") or headers.get("Authorization", "").replace("Bearer ", "")
        
        if api_key and self._is_valid_api_key(api_key):
            # In a real system, you'd lookup the agent_id or user_id associated with this key
            actor_id = self._get_actor_for_api_key(api_key)
            return True, actor_id, "agent"
            
        # 2. Check for User session token (Browser access via Supabase Auth)
        # Normally handled by Supabase middleware, but here is the manual fallback
        token = headers.get("Authorization", "").replace("Bearer ", "")
        if token and self.client:
            try:
                user = self.client.auth.get_user(token)
                if user and user.user:
                    return True, user.user.id, "user"
            except Exception as e:
                print(f"[Auth] JWT validation failed: {e}")
                
        return False, None, None

    def _is_valid_api_key(self, api_key: str) -> bool:
        """Validate API key format/presence (stub)."""
        # Stub implementation
        return len(api_key) > 20 and api_key.startswith("gm_")

    def _get_actor_for_api_key(self, api_key: str) -> str:
        """Lookup the actor ID for a given API key (stub)."""
        # Stub implementation
        return "system_agent"
