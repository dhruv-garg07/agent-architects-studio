import sys
import os

# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Get the parent directory (one level up)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

# Add parent directory to sys.path
sys.path.insert(0, parent_dir)
print(parent_dir)
# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Go two levels up
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

# Add to sys.path
sys.path.insert(0, grandparent_dir)


from backend_examples.python.services.profiles import profile_Service
from LLM_calls.together_get_response import stream_chat_response
from utlis.utlis_functions import extract_json_from_string
from Octave_mem.RAG_DB_CONTROLLER.utlis_docs.doc_control_chunks import process_file, fast_tag_extractor
from RAG_DB.chroma_collection_manager import ChromaCollectionManager
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os   
import time
load_dotenv()

# user_id is same as collection name
class read_data_RAG:
    def __init__(self, database: str = None):
        if database is None:
            database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        self.manager = ChromaCollectionManager(database=database)
    
    def fetch(self, user_ID: str, top_k: int = 5) -> List[Dict]:
        """
        Fetch all chat history for a given user_ID (collection name).
        
        Args:
            user_ID (str): The user ID or collection name.
            top_k (int): Number of top similar documents to retrieve."""
        collection = self.manager.get_collection(user_ID)
        if collection is None:
            print(f"Collection {user_ID} does not exist.")
            return []
        # print(collection.items())
        try:
            results = collection.query(
                query_texts=[""],  # Empty query to fetch all documents
                n_results=top_k
            )
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            chat_history = []
            for doc, meta in zip(documents, metadatas):
                chat_history.append({
                    "document": doc,
                    "metadata": meta
                })
            
            return chat_history
        except Exception as e:
            print(f"Error fetching chat history for {user_ID}: {e}")
            return []
    
    def fetch_with_filter(
        self, 
        user_ID: str, 
        filter_metadata: Dict, 
        top_k: int = 5
    ) -> List[Dict]:
        """
        Fetch chat history for a given user_ID (collection name) with metadata filtering.
        
        Args:
            user_ID (str): The user ID or collection name.
            filter_metadata (Dict): Metadata filter to apply.
            top_k (int): Number of top similar documents to retrieve.
        """
        collection = self.manager.get_collection(user_ID)
        if collection is None:
            print(f"Collection {user_ID} does not exist.")
            return []
        
        try:
            results = collection.query(
                query_texts=[""],  # Empty query to fetch all documents
                n_results=top_k,
                where=filter_metadata
            )
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            chat_history = []
            for doc, meta in zip(documents, metadatas):
                chat_history.append({
                    "document": doc,
                    "metadata": meta
                })
            
            return chat_history
        except Exception as e:
            print(f"Error fetching filtered chat history for {user_ID}: {e}")
            return []
        
   # In your controller (or add a new method if you prefer)
    def fetch_related_to_query(
        self,
        user_ID: str,
        query: str,
        top_k: int = 5
    ) -> list[dict]:
        collection = self.manager.get_collection(user_ID)
        if collection is None:
            print(f"Collection {user_ID} does not exist.")
            return []

        try:
            results = collection.query(query_texts=[query], n_results=top_k)
            # results like:
            # {'ids': [[...]], 'distances': [[...]], 'documents': [[...]], 'metadatas': [[...]] ...}
            ids        = results.get("ids", [[]])[0]
            docs       = results.get("documents", [[]])[0]
            metadatas  = results.get("metadatas", [[]])[0]
            distances  = results.get("distances", [[]])[0]  # lower is better in Chroma

            out = []
            for i, (id_, doc, meta, dist) in enumerate(zip(ids, docs, metadatas, distances)):
                out.append({
                    "id": id_,
                    "document": doc,
                    "metadata": meta,
                    "distance": float(dist),  # keep raw distance; we'll convert to score in API
                })
            return out
        except Exception as e:
            print(f"Error fetching chat history related to query for {user_ID}: {e}")
            return []

    def fetch_with_id(
        self, 
        user_ID: str, 
        doc_id: str
    ) -> Optional[Dict]:
        """
        Fetch a specific chat entry by its document ID.
        
        Args:
            user_ID (str): The user ID or collection name.
            doc_id (str): The document ID to fetch.
        
        Returns:
            Dict: The chat entry with document and metadata, or None if not found.
        """
        collection = self.manager.get_collection(user_ID)
        if collection is None:
            print(f"Collection {user_ID} does not exist.")
            return None
        
        try:
            results = collection.get(ids=[doc_id])
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            if documents and metadatas:
                return {
                    "document": documents[0],
                    "metadata": metadatas[0]
                }
            else:
                print(f"Document ID {doc_id} not found in collection {user_ID}.")
                return None
        except Exception as e:
            print(f"Error fetching chat history by ID for {user_ID}: {e}")
            return None

    def fetch_by_conversation_thread(self, user_id: str, conversation_thread: str, top_k: int = 5) -> List[Dict]:
        """
        Fetch chat history for a given conversation thread.
        
        Args:
            conversation_thread (str): The conversation thread ID.
            top_k (int): Number of top similar documents to retrieve.
        """
        try:
            # Assuming conversation_thread is stored in metadata
            filter_metadata = {"conversation_thread": conversation_thread}
            results = self.manager.get_collection(user_id).query(
                query_texts=[""],  # Empty query to fetch all documents
                # n_results=top_k,
                where=filter_metadata
            )
            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            chat_history = []
            for id, doc, meta in zip(ids, documents, metadatas):
                chat_history.append({
                    "id": id,
                    "document": doc,
                    "metadata": meta
                })
            
            return chat_history
        except Exception as e:
            print(f"Error fetching chat history for conversation thread {conversation_thread}: {e}")
            return []
        
    async def profile_info_by_id(self, id: str):
        """Get profile info from Supabase."""
        try:
            profile = await profile_Service.fetch_profile_by_id(id)
            if profile:
                return {
                    "id": profile.id,
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "user_role": profile.user_role,
                    "portfolio_url": profile.portfolio_url,
                    "expertise": profile.expertise,
                    "primary_interest": profile.primary_interest,
                    "github_url": profile.github_url,
                    "email": profile.email,
                    "created_at": profile.created_at,
                    "memory": profile.memory
                }
            return None
        except Exception as e:
            print(f"Error getting profile info: {e}")
            return None
    
    async def profile_info_by_username(self, username: str):
        """Get profile info from Supabase by username."""
        try:
            profile = await profile_Service.fetch_profile_by_username(username)
            if profile:
                return {
                    "id": profile.id,
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "user_role": profile.user_role,
                    "portfolio_url": profile.portfolio_url,
                    "expertise": profile.expertise,
                    "primary_interest": profile.primary_interest,
                    "github_url": profile.github_url,
                    "email": profile.email,
                    "created_at": profile.created_at,
                    "memory": profile.memory
                }
            return None
        except Exception as e:
            print(f"Error getting profile info by username: {e}")
            return None

    async def update_user_memory(self, id: str, memory: List[str]) -> Optional[Dict]:
        """Update the user's memory field."""
        try:
            profile = await profile_Service.update_user_memory(id, memory)
            if profile:
                return {
                    "id": profile.id,
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "user_role": profile.user_role,
                    "portfolio_url": profile.portfolio_url,
                    "expertise": profile.expertise,
                    "primary_interest": profile.primary_interest,
                    "github_url": profile.github_url,
                    "email": profile.email,
                    "created_at": profile.created_at,
                    "memory": profile.memory
                }
            return None
        except Exception as e:
            print(f"Error updating user memory: {e}")
            return None

    async def append_sessionid_to_memory(self, id: str, session_id: str) -> Optional[Dict]:
        """Append a new session ID to the user's memory list."""
        try:
            profile = await profile_Service.fetch_profile_by_id(id)
            if profile:
                current_memory = profile.memory or []
                if session_id not in current_memory:
                    current_memory.append(session_id)
                    updated_profile = await profile_Service.update_user_memory(id, current_memory)
                    if updated_profile:
                        return {
                            "id": updated_profile.id,
                            "username": updated_profile.username,
                            "full_name": updated_profile.full_name,
                            "user_role": updated_profile.user_role,
                            "portfolio_url": updated_profile.portfolio_url,
                            "expertise": updated_profile.expertise,
                            "primary_interest": updated_profile.primary_interest,
                            "github_url": updated_profile.github_url,
                            "email": updated_profile.email,
                            "created_at": updated_profile.created_at,
                            "memory": updated_profile.memory
                        }
            return None
        except Exception as e:
            print(f"Error appending session ID to memory: {e}")
            return None

    async def list_session_ids(self, id: str) -> Optional[List[str]]:
        """List all session IDs in the user's memory field."""
        try:
            profile = await profile_Service.fetch_profile_by_id(id)
            if profile:
                return profile.memory or []
            return None
        except Exception as e:
            print(f"Error listing session IDs: {e}")
            return None
        
    async def create_session(self, id: str, thread_id: str, created: str) -> Optional[str]:
        """Create a new session ID and append it to the user's memory."""
        try:
            profile = await profile_Service.fetch_profile_by_id(id)
            if profile:
                current_memory = profile.memory or []
                if thread_id not in current_memory:
                    current_memory.append(thread_id)
                    updated_profile = await profile_Service.update_user_memory(id, current_memory)
                    if updated_profile:
                        return thread_id
            return None
        except Exception as e:
            print(f"Error creating session: {e}")
            return None
# Dhruv look at examples to call from index.py
if __name__ == "__main__":
    reader = read_data_RAG(database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"))
    user_id = "2cdaa777-c623-4912-96ff-6449e8bca7ed"
    # chat_history = reader.fetch(user_ID=user_id, top_k=2)
    # print(f"Chat history for {user_id}:")
    # for entry in chat_history:
    #     print(entry)
    
    # # Example of fetching with metadata filter
    # filter_meta = {"index": 10}
    # filtered_history = reader.fetch_with_filter(user_ID=user_id, filter_metadata=filter_meta, top_k=2)
    # print(f"\nFiltered chat history for {user_id} with metadata {filter_meta}:  ")
    # for entry in filtered_history:
    #     print(entry)
        
    # # Example of fetching related to a query
    # query_text = "image is recieved"        
    # related_history = reader.fetch_related_to_query(user_ID=user_id, query=query_text, top_k=2)
    # print(f"\nChat history for {user_id} related to query '{query_text}':  ")
    # for entry in related_history:        
    #     print(entry)

#     # Example of fetching by document ID
#     doc_id = "id_5"
#     entry_by_id = reader.fetch_with_id(user_ID=user_id, doc_id=doc_id)
#     print(f"\nChat entry for {user_id} with document ID '{doc_id  }':  ") 
#     print(entry_by_id)

#    # Example of fetching by conversation thread   
    conversation_thread = "f0fe53e8-4813-4dcb-a365-f767c0cd888b"  # Replace with an actual thread ID
    thread_history = reader.fetch_by_conversation_thread(user_id=user_id, conversation_thread=conversation_thread, top_k=2)
    print(f"\nChat history for conversation thread '{conversation_thread}':  ")       
    for entry in thread_history:        
        print(entry)

# import asyncio
# if __name__ == "__main__":
#     reader = read_data_RAG(database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"))
#     id = "2cdaa777-c623-4912-96ff-6449e8bca7ed"
#     profile_info = asyncio.run(reader.profile_info_by_id(id=id))
#     print(f"Profile info for {id}: {profile_info}")
    
#     username = "sanketwadhwa"
#     profile_info_username = asyncio.run(reader.profile_info_by_username(username=username))
#     print(f"Profile info for username {username}: {profile_info_username}")
    
#     # Example of update user_memory:
#     # memory = [f"NEW_SESSION_ID", "ANOTHER_SESSION_ID"]
#     # updated_profile = asyncio.run(reader.update_user_memory(id=id, memory=memory))  
    
#     # Example of append session_id to user_memory:
#     session_id = "APPENDED_SESSION_ID_2"  
#     appended_profile = asyncio.run(reader.append_sessionid_to_memory(id=id, session_id=session_id))
#     print(f"Appended profile info for {id}: {appended_profile}")
    
#     # Example of list all session_ids in user_memory:
#     session_ids = asyncio.run(reader.list_session_ids(id=id))   
#     print(f"Session IDs for {id}: {session_ids}")