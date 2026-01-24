import os
import sys  
from typing import List, Optional

# Add backend_examples/python to path for model imports
backend_python_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_python_dir not in sys.path:
    sys.path.insert(0, backend_python_dir)

# Now safe to import Profile from backend_examples.python.models
from backend_examples.python.models import Profile

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lmlwkkbzkikrkshriaqm.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtbHdra2J6a2lrcmtzaHJpYXFtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYxNDEzMDUsImV4cCI6MjA3MTcxNzMwNX0.v2dO6pscKXPxCmjUCAQW0EXVTV_iAN9BWQ7crX4yNUc")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_supabase_client() -> Client:
    """Get the Supabase client instance."""
    return supabase


# def supabase_update_profile(user_id, update_data):
#     try:
#         response = supabase_backend.table('profiles').update(update_data).eq('id', user_id).execute()
#         if response.data:
#             return response.data[0]
#         return None
#     except Exception as e:
#         print(f"Error updating profile for {user_id}: {e}")
#         return None

class profileService:
    """Service for managing user profiles."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def fetch_profile_by_id(self, id: str) -> Optional[Profile]:
        """Fetch a user profile by id."""
        try:
            response = self.supabase.table('profiles').select('*').eq('id', id).execute()
            if response.data:   
                return Profile(**response.data[0])   
            return None
        except Exception as e:
            print(f"Error fetching profile for {id}: {e}")
            return None 
    
    async def update_profile(self, id: str, update_data: dict) -> Optional[Profile]:
        """Update a user profile."""
        try:
            response = self.supabase.table('profiles').update(update_data).eq('id', id).execute()
            if response.data:
                return Profile(**response.data[0])
            return None
        except Exception as e:
            print(f"Error updating profile for {id}: {e}")
            return None
    
    async def fetch_profile_by_username(self, username: str) -> Optional[Profile]:
        """Fetch a user profile by username."""
        try:
            response = self.supabase.table('profiles').select('*').eq('username', username).execute()
            if response.data:
                return Profile(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching profile for username {username}: {e}")
            return None
    
    async def update_user_memory(self, id: str, memory: List[str]) -> Optional[Profile]:
        """Update the user's memory field."""
        try:
            response = self.supabase.table('profiles').update({
                'memory': memory
            }).eq('id', id).execute()
            
            if response.data:
                return Profile(**response.data[0])
            return None
            
        except Exception as e:
            print(f"Error updating memory for {id}: {e}")
            return None
        
profile_Service = profileService()