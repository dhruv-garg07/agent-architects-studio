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

def add_message(user_id: str, role: str, content: str, session_id: str = None):
    """
    Handles both session creation (Insert) and message appending (Update).
    NOTE: Prone to race conditions on the update path.
    """
    # 1. Prepare the new message object
    new_message_obj = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Generate ID if not provided (i.e., new session)
    if not session_id:
        session_id = str(uuid.uuid4())
    
    table = supabase.table("chat_sessions")

    # --- ATTEMPT 1: CHECK FOR EXISTING ROW (The 'R' in Read-Modify-Write) ---
    try:
        # Fetch the messages column for the specific session_id
        response = table.select("messages").eq("id", session_id).single().execute()
        
        # If the row exists, response.data will contain the current messages
        if response.data and response.data['messages'] is not None:
            # --- UPDATE PATH ---
            current_messages = response.data['messages']
            
            # 2. Modify: Append the new message in Python
            current_messages.append(new_message_obj)
            
            # 3. Write: Send the entire modified list back (The 'W' in Read-Modify-Write)
            update_response = table.update({
                "messages": current_messages,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
            
            print(f"✅ Appended message to existing session: {session_id}")
            return session_id
        
    except APIError as e:
        # If the query fails to find the row (e.g., 'single' filter returns no row),
        # we fall through to the INSERT path.
        if 'PostgrestException: JSON object must be single' not in str(e):
             # Handle other, real exceptions
             pass

    # --- ATTEMPT 2: INSERT NEW ROW (If no row was found) ---
    
    # If we reached here, the session_id does not exist, so we insert.
    insert_data = {
        "id": session_id,
        "user_id": user_id,
        "title": content[:50], # Use first 50 chars as temporary title
        "messages": [new_message_obj] # Start with a list containing 1 item
    }
    
    try:
        table.insert(insert_data).execute()
        print(f"✅ Created new session: {session_id}")
        return session_id
        
    except Exception as e:
        # This handles the case where another process might have inserted 
        # the session between our 'select' and 'insert' attempts (A different type of race).
        print(f"⚠️ Insertion failed (possible conflict): {e}")
        # In a real app, you would log this error or retry the operation here.
        return None
    
def get_chat_history_by_session(user_id: str, session_id: str, top_k: int = 10):
    """
    Fetch chat history for a given user and session (thread) from Supabase.
    Args:
        user_id (str): The user ID.
        session_id (str): The session/thread ID.
        top_k (int, optional): Number of top messages to return (most recent if sorted by timestamp).
    Returns:
        List[Dict]: List of chat messages sorted by timestamp (ascending).
    """
    table = supabase.table("chat_sessions")
    print(f"Fetching chat history for session {session_id} and user {user_id}")
    try:
        response = table.select("messages").eq("id", session_id).eq("user_id", user_id).single().execute()
        messages = response.data.get("messages", []) if response.data else []
        # Sort messages by timestamp if present
        messages.sort(key=lambda x: x.get("timestamp", ""))
        if top_k is not None:
            messages = messages[-top_k:]  # Get the most recent top_k messages
        return messages
    except Exception as e:
        print(f"Error fetching chat history for session {session_id}: {e}")
        return []

# # Assuming 'add_message' is defined and Supabase client is initialized.

# user_id = "2cdaa777-c623-4912-96ff-6449e8bca7ed" # ID of the logged-in user

# # --- FIRST MESSAGE (Session Creation) ---
# print("User: Hey there, this is the second message in a new session.")

# # We intentionally set session_id=None (or just omit it)
# new_session_id = add_message(
#     user_id=user_id,
#     role="user",
#     content="Can you summarize the key points from the Q3 report?",
#     session_id="6569bdd2-001c-4a32-92b7-789ae51e678c"
#     # session_id is omitted here! 
# )

# # Store this ID, which was generated and returned by the function.
# print(f"✅ New Session Created with ID: {new_session_id}")

# current_session_id = new_session_id