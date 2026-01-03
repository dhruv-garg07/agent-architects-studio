import uuid
from datetime import datetime, timezone
from supabase import create_client, Client
from postgrest.exceptions import APIError
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables or .env file.")
supabase: Client = create_client(url, key)

# CRUD operations for the SQL DB Controller for agents with a supabase table called as: "agent_sessions"

class Agent_Chat_Manager():
    """
    This is a controller class to manage agents and their chat histories in the SQL DB (Supabase).
    It includes APIs for both the file and the chat history uploads and retrievals.
    Each collection name in the chroma DB is the agent ID.
    CRUD operations of the agents includes CRUD on collection corresponding to that agent ID.
    """

    TABLE_NAME = "agent_sessions"

    def __init__(self):
        self.table = supabase.table(self.TABLE_NAME)

    def create_agent_session(self, user_id: str, agent_id: str) -> str:
        """Create a new agent session."""
        session_id = str(uuid.uuid4())
        payload = {
            "id": session_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self.table.insert(payload).execute()
        return session_id

    def delete_agent_session(self, session_id: str) -> bool:
        """Delete an agent session."""
        response = self.table.delete().eq("id", session_id).execute()
        return response.status_code == 200
    
    def add_message_to_session(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to an existing agent session."""
        new_message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        # Fetch current messages
        response = self.table.select("messages").eq("id", session_id).single().execute()
        if response.data and response.data['messages'] is not None:
            current_messages = response.data['messages']
            current_messages.append(new_message)
            # Update messages
            update_response = self.table.update({
                "messages": current_messages,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
            return update_response.status_code == 200
        return False
    
    def get_session_messages(self, session_id: str) -> list:
        """Retrieve messages from an agent session."""
        response = self.table.select("messages").eq("id", session_id).single().execute()
        if response.data and response.data['messages'] is not None:
            return response.data['messages']
        return []
    
    def list_sessions_for_agent(self, agent_id: str, user_id: str) -> list:
        """List all sessions for a given agent and user."""
        response = self.table.select("*").eq("agent_id", agent_id).eq("user_id", user_id).execute()
        if response.data:
            return response.data
        return []
    
    