from LLM_calls.together_get_response import stream_chat_response, extract_output_after_think
from utlis.utlis_functions import extract_json_from_string
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
class RAG_DB_Controller:
    def __init__(self, database: str = None):
        """Initialize the controller with ChromaCollectionWrapper."""
        load_dotenv()
        if database is None:
            database = os.getenv("CHROMA_DATABASE")
        self.wrapper = ChromaCollectionWrapper(database=database)
    
    def update_DB_with_LLM(user_ID: str):
        """Update the RAG DB using LLM calls and verify the operation."""
        
        # next_id = self.wrapper.get_collection_info(f"{user_ID}")["document_count"]
        prompt = f"""
        You are an AI assistant that helps to update the RAG DB with new data.
        The RAG DB is a ChromaDB collection that stores documents with their IDs and metadata
        You will be provided with the data that has to be stored. Do not modify the data.
        """
        json_task_write_data = extract_json_from_string(extract_output_after_think(stream_chat_response(prompt=prompt)))