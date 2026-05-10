"""
GitMem v2.0 — User Search

Enables searching for users by email or username to invite them to
workspaces or repositories.
"""

from typing import List, Dict, Any


class UserSearch:
    """Searches for users in the system."""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self._table = "users" # Assuming a public or readable users profile table exists

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for users by email or username.
        Note: Supabase auth.users is private. This assumes a public 'users' or 'profiles' table.
        """
        if not self.client or len(query) < 3:
            return []
            
        try:
            # Using ilike for case-insensitive search
            res = self.client.table(self._table) \
                .select("id, email, full_name, avatar_url") \
                .or_(f"email.ilike.%{query}%,full_name.ilike.%{query}%") \
                .limit(limit) \
                .execute()
            return res.data or []
        except Exception as e:
            print(f"[UserSearch] Search failed: {e}")
            return []

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Exact match lookup by email."""
        if not self.client:
            return None
        try:
            res = self.client.table(self._table).select("*").eq("email", email).execute()
            return res.data[0] if res.data else None
        except Exception:
            return None
