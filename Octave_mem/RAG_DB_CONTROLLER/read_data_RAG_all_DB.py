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
        
    def fetch_related_to_query(
        self, 
        user_ID: str, 
        query: str, 
        top_k: int = 5
    ) -> List[Dict]:
        """
        Fetch chat history for a given user_ID (collection name) related to a specific query.
        
        Args:
            user_ID (str): The user ID or collection name.
            query (str): The query text to find related documents.
            top_k (int): Number of top similar documents to retrieve.
        """
        collection = self.manager.get_collection(user_ID)
        if collection is None:
            print(f"Collection {user_ID} does not exist.")
            return []
        
        try:
            results = collection.query(
                query_texts=[query],
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


# Dhruv look at examples to call from index.py
# if __name__ == "__main__":
#     reader = read_data_RAG(database=os.getenv("CHROMA_DATABASE_FILE_DATA"))
#     user_id = "user1234"
#     chat_history = reader.fetch(user_ID=user_id, top_k=2)
#     print(f"Chat history for {user_id}:")
#     for entry in chat_history:
#         print(entry)
    
#     # Example of fetching with metadata filter
#     filter_meta = {"index": 10}
#     filtered_history = reader.fetch_with_filter(user_ID=user_id, filter_metadata=filter_meta, top_k=2)
#     print(f"\nFiltered chat history for {user_id} with metadata {filter_meta}:  ")
#     for entry in filtered_history:
#         print(entry)
        
#     # Example of fetching related to a query
#     query_text = "image is recieved"        
#     related_history = reader.fetch_related_to_query(user_ID=user_id, query=query_text, top_k=2)
#     print(f"\nChat history for {user_id} related to query '{query_text}':  ")
#     for entry in related_history:        
#         print(entry)

#     # Example of fetching by document ID
#     doc_id = "id_5"
#     entry_by_id = reader.fetch_with_id(user_ID=user_id, doc_id=doc_id)
#     print(f"\nChat entry for {user_id} with document ID '{doc_id  }':  ") 
#     print(entry_by_id)
