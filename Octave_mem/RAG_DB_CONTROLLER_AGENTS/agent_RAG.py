"""
This file a standalone file api_manhattan to call. All the agent apis should be here.
It includes apis for both the file and the chat history uploads and retrievals.
Each collection name in the chroma DB is the agent ID.
CRUD operations of the agents includes CRUD on collection corresponding to that agent ID.
"""

from RAG_DB.chroma_collection_wrapper import ChromaCollectionWrapper
from RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG
from dotenv import load_dotenv
import os
from typing import List, Dict, Optional
load_dotenv()

class Agentic_RAG:
    def __init__(self, database: str = None):
        """Initialize the controller with ChromaCollectionWrapper."""
        load_dotenv()
        if database is None:
            database = os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        self.wrapper = ChromaCollectionWrapper(database=database)
        self.read_controller = read_data_RAG(database=database)
    
    def create_agent_collection(self, agent_ID: str):
        """Create a new collection for the agent."""
        return self.wrapper.manager.create_collection(collection_name=agent_ID)
    
    def delete_agent_collection(self, agent_ID: str):
        """Delete the collection for the agent."""
        return self.wrapper.manager.delete_collection(collection_name=agent_ID)
    
    # CRUD operations for chat history can be added here as needed.
    def add_docs(self,agent_ID: str, ids: List[str], documents: List[str], metadatas: Optional[List[Dict]] = None
    ) -> Dict:
        """Add chat history to the agent's collection with verification."""
        return self.wrapper.create_or_update_collection_with_verify(
            collection_name=agent_ID,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
    def get_agent_collection_info(self, agent_ID: str) -> Dict:
        """Get information about the agent's collection."""
        return self.wrapper.get_collection_info(collection_name=agent_ID)
    
    
    # Search operations on one COLLECTION (agent_ID)
    #  === READ OPERATIONS ==== 
    def search_agent_collection(
        self,
        agent_ID: str,
        query: str,
        n_results: int = 5,
        include_metadata: bool = True
    ):
        """Search an agent collection for documents related to `query`.

        This delegates to `read_controller.fetch_related_to_query` and returns a list of
        dicts: {id, document, metadata, distance} where `distance` is the raw chroma distance
        (lower = more similar). If the collection does not exist or an error occurs, an empty
        list is returned.
        """
        try:
            results = self.read_controller.fetch_related_to_query(agent_ID, query, top_k=n_results)
            return results or []
        except Exception as e:
            print(f"[Agentic_Chat_Manager] search_agent_collection error for {agent_ID}: {e}")
            return []

    def fetch_history(self, agent_ID: str, top_k: int = 50) -> List[Dict]:
        """Fetch recent chat history for an agent (collection).

        Returns a list of entries: each entry is {'document': <text>, 'metadata': <dict>}.
        """
        try:
            return self.read_controller.fetch(user_ID=agent_ID, top_k=top_k) or []
        except Exception as e:
            print(f"[Agentic_Chat_Manager] fetch_history error for {agent_ID}: {e}")
            return []

    def get_message_by_id(self, agent_ID: str, doc_id: str) -> Optional[Dict]:
        """Retrieve a single message/document by its document id within the agent collection."""
        try:
            return self.read_controller.fetch_with_id(user_ID=agent_ID, doc_id=doc_id)
        except Exception as e:
            print(f"[Agentic_Chat_Manager] get_message_by_id error for {agent_ID}:{doc_id}: {e}")
            return None

    def fetch_with_filter(self, agent_ID: str, filter_metadata: Dict, top_k: int = 50) -> List[Dict]:
        """Fetch chat history with a metadata filter (delegate to read_controller.fetch_with_filter)."""
        try:
            return self.read_controller.fetch_with_filter(user_ID=agent_ID, filter_metadata=filter_metadata, top_k=top_k) or []
        except Exception as e:
            print(f"[Agentic_Chat_Manager] fetch_with_filter error for {agent_ID}: {e}")
            return []
        
    # UPDATE operations
    def update_docs(
        self,
        agent_ID: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict:
        """Update chat history in the agent's collection with verification."""
        return self.wrapper.update_collection_with_verify(
            collection_name=agent_ID,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def update_doc_metadata(
        self,
        agent_ID: str,
        ids: List[str],
        metadatas: List[Dict]
    ) -> Dict:
        """Update metadata of chat history entries in the agent's collection with verification."""
        return self.wrapper.update_collection_metadata_with_verify(
            collection_name=agent_ID,
            ids=ids,
            metadatas=metadatas
        )
    
    # DELETE operations
    def delete_chat_history(
        self,
        agent_ID: str,
        ids: List[str]
    ) -> Dict:
        """Delete chat history entries from the agent's collection with verification."""
        return self.wrapper.delete_documents_with_verify(
            collection_name=agent_ID,
            ids=ids
        )