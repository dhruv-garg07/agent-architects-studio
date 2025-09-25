import sys
import os

# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Get the parent directory (one level up)
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

# Add parent directory to sys.path
sys.path.insert(0, parent_dir)
print(parent_dir)
import sys
import os

# Get the current file's directory
current_dir = os.path.dirname(__file__)

# Go two levels up
grandparent_dir = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))

# Add to sys.path
sys.path.insert(0, grandparent_dir)

# Now you can import or access files/modules from two levels above
# Now you can import modules or access files from one level up
# Example: from parent_module import something

from LLM_calls.together_get_response import stream_chat_response
from utlis.utlis_functions import extract_json_from_string
from Octave_mem.RAG_DB_CONTROLLER.utlis_docs.doc_control_chunks import process_file, fast_tag_extractor
from RAG_DB.chroma_collection_wrapper import ChromaCollectionWrapper
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os   
load_dotenv()

SAMPLE_OPERATION = [{
            "type": "create_or_update",
            "collection_name": "test_collection_1",
            "ids": ["id6", "id4"],
            "documents": ["doc1123", "doc122"],
            "metadatas": [{"cat": "1234213"}, {"cat234": "q134223"}]
        },
        
        {
            "type": "update",
            "collection_name": "test_collection_1",
            "ids": ["id7"],
            "documents": ["doc4"],
            "metadatas": [{"cats": "D"}]
        },
        {
            "type": "replace",
            "collection_name": "test_collection_1",
            "ids": ["new_id1", "new_id2"],
            "documents": ["new_doc1", "new_doc2"],
            "metadatas": [{"cat": "X"}, {"cat": "Y"}]
        }]

# Write a class that handles the data writing to the RAG DB with verification.

# Intended tasks of a controller are to manage the Session and data for a particular user.
# We already have class ChromaCollectionWrapper and in that class we have methods that combine operations with verification.
# ChromaCollectionWrapper.bulk_operations_with_verification() exists to update the database.
# It needs {
        #     "type": "create_or_update",
        #     "collection_name": "test_collection_1",
        #     "ids": ["id6", "id4"],
        #     "documents": ["doc1123", "doc122"],
        #     "metadatas": [{"cat": "1234213"}, {"cat234": "q134223"}]
        # }, 
        
# 1. Type will always be "create_or_update" for now.
# 2. collection_name will be the user_ID.
# 3. ids -> Will be managed by a ID manager.
# 4. Docs are actual chat sessions.
# 5. Metadatas -> Will be managed by a metadata manager.




import time
class RAG_DB_Controller_FILE_DATA:
    def __init__(self, database: str = None):
        """Initialize the controller with ChromaCollectionWrapper."""
        load_dotenv()
        if database is None:
            database = os.getenv("CHROMA_DATABASE_FILE_DATA")
        self.wrapper = ChromaCollectionWrapper(database=database)
    
    # Returns next available ID for a user.
    def id_manager(self, user_ID: str) -> int:
        """Get the next ID for a user."""
        next_id = self.wrapper.get_collection_info(f"{user_ID}").get("document_count", 0)
        return next_id + 1  # Increment to get the next available ID.
    
    # Returns a new conversation thread ID for linking messages. Should be invoked for a new chat.
    def get_new_conversation_thread_id(self, user_ID: str) -> str:
        """Get or create a conversation thread ID for linking messages."""
        # You can implement logic to get the current active thread
        # For simplicity, using a fixed thread or timestamp-based thread
        return f"thread_{int(time.time())}"
    
    # Extract metadata using LLM calls.
    def extract_metadata_via_llm(self, content_data: str, message_type: str = "user") -> Dict:
        """Extract metadata using LLM calls."""
        if message_type == "user":
            metadata_prompt = f"""
            Extract key topics or keywords from the following user message for metadata tagging: {content_data}
            Give the response in a few words only."""
        else:  # LLM message
            metadata_prompt = f"""
            Extract key topics or keywords from the following AI response for metadata tagging: {content_data}
            Give the response in a few words only."""
        
        metadata_response = stream_chat_response(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", 
            max_tokens=20, 
            prompt=metadata_prompt, 
            temperature=0.3
        )
        response = ""
        for token in metadata_response:
            response += token
        return response
    
    def send_data_to_rag_db(self, user_ID: str, chunks: list[str], message_type: str = "user", file_path: Optional[str] = None, file_name: Optional[str] = None):
        """Send data to RAG DB with metadata extraction and verification."""
        # file_path = os.path.basename(file_path)

        if chunks is None or len(chunks) == 0:
            print("No chunks to process.")
            return {"error": "No chunks to process."}
        
        ids = []
        documents = []
        metadatas = []
        for chunk in chunks:
            if not isinstance(chunk, str) or len(chunk.strip()) == 0:
                print(f"Invalid chunk: {chunk}")
                return {"error": f"Invalid chunk: {chunk}"}
            
            next_id = self.id_manager(user_ID)
            metadata_response =  fast_tag_extractor(chunk, top_n=3)

            operation = {
                "type": "create_or_update",
                "collection_name": user_ID,
                "ids": [f"id_{next_id}"],
                "documents": [chunk],
                "metadatas": [{
                    "source": f"{file_name}",
                    "index": next_id,
                    "message_type": message_type,
                    "timestamp": time.time(),
                    "tags": metadata_response,
                }]
            }
            
            verification_result = self.wrapper.bulk_operations_with_verification([operation])
        return verification_result
    
    def update_file_data_to_db(self, user_ID: str, file_path: str, message_type: str = "user", file_name: Optional[str] = None):
        """Process file and send data to RAG DB."""
        chunks = process_file(file_path=file_path)
        if chunks is None or len(chunks) == 0:
            print("No chunks extracted from the file.")
            return {"error": "No chunks extracted from the file."}
        
        verification_result = self.send_data_to_rag_db(user_ID=user_ID, chunks=chunks, message_type=message_type, file_path=file_path, file_name=file_name)
        return verification_result

# Example usage:
# Better to manage sessions outside this class.

# 1. Database - Chat history, Manual data, file uploads, external API.
# controller_chatH = RAG_DB_Controller_CHAT_HISTORY(database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"))  
# result = controller_chatH.send_data_to_rag_db(user_ID="user123", content_data="You are good at it no need to improve it.", is_reply_to=1, message_type="llm", conversation_thread="thread_1758555372")
# print(result)

# 2. Database - FILE UPLOADS
# A different database for file uploads and other manual data.
# Difference in metadata:
# 1. Metadata extraction might differ
# 2. message_type will always be "user" for file uploads.
# 3. No is_reply_to 
# 4.
# file_path="C:/Users/Dellg/Downloads/EE316 Min2 sols.pdf"
# # chunks = process_file(file_path=file_path)
# # for chunk in chunks:
# #     print(chunk, "\n---\n")

# controller_file_data = RAG_DB_Controller_FILE_DATA(database=os.getenv("CHROMA_DATABASE_FILE_DATA"))
# controller_file_data.update_file_data_to_db(user_ID="user1234", file_path=file_path, message_type="user")
# NEW DATA 
