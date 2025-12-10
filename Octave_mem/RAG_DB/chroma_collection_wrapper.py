import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from RAG_DB.chroma_collection_manager import ChromaCollectionManager

class ChromaCollectionWrapper:
    def __init__(self, database: str = None):
        """Initialize the wrapper with ChromaCollectionManager."""
        load_dotenv()
        if database is None:
            database = os.getenv("CHROMA_DATABASE_FILE_DATA")
        self.manager = ChromaCollectionManager(database=database)
    
    def create_or_update_collection_with_verify(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create or update collection and automatically verify the operation.
        
        Returns:
            Dict with operation result and verification details.
        """
        
        print("Reached inside create or update with verify")
        # Perform the operation
        result = self.manager.create_or_update_collection(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        # Verify the operation
        verification = self.manager.verify_data_in_collection(
            collection_name=collection_name,
            expected_ids=ids
        )
        
        return {
            "operation": "create_or_update_collection",
            "result": result,
            "verification": verification,
            "success": "error" not in verification and verification.get("ids_match", False)
        }
    
    def update_collection_with_verify(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Update collection and automatically verify the operation.
        
        Returns:
            Dict with operation result and verification details.
        """
        # Perform the operation
        result = self.manager.update_collection(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        # Verify the operation - get all IDs to see what's actually there
        verification = self.manager.verify_data_in_collection(
            collection_name=collection_name
        )
        
        # Check if our new IDs are in the collection
        actual_ids = set(verification.get("actual_ids", []))
        expected_ids = set(ids)
        ids_present = expected_ids.issubset(actual_ids)
        
        return {
            "operation": "update_collection",
            "result": result,
            "verification": verification,
            "success": "error" not in verification and ids_present,
            "new_ids_added": list(expected_ids),
            "all_ids_in_collection": list(actual_ids)
        }
    
    def replace_collection_with_verify(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Replace collection and automatically verify the operation.
        
        Returns:
            Dict with operation result and verification details.
        """
        # Perform the operation
        result = self.manager.replace_collection(
            collection_name=collection_name,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        # Verify the operation
        if ids and documents:
            verification = self.manager.verify_data_in_collection(
                collection_name=collection_name,
                expected_ids=ids
            )
            success = "error" not in verification and verification.get("ids_match", False)
        else:
            verification = self.manager.verify_data_in_collection(collection_name)
            success = "error" not in verification and verification.get("document_count", 0) == 0
        
        return {
            "operation": "replace_collection",
            "result": result,
            "verification": verification,
            "success": success
        }
    
    def bulk_operations_with_verification(
        self,
        operations: List[Dict]
    ) -> List[Dict]:
        """
        Perform multiple create_or_update operations with verification.

        Assumes every operation in `operations` is a create_or_update operation
        and uses the existing create_or_update_collection_with_verify (which
        performs an upsert under the hood). Processing is done with a list
        comprehension to avoid using an explicit for-loop.
        """
        # Use list comprehension (no explicit for-loop) to process all operations
        
        ids = []
        documents = []
        metadatas = []
        for op in operations:
            ids.extend(op.get("ids", []))
            documents.extend(op.get("documents", []))
            metadatas.extend(op.get("metadatas", []))
        
        collection_name = operations[0].get("collection_name") if operations else "default_collection"
        results = [
            self.create_or_update_collection_with_verify(
                collection_name=collection_name,
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
        ]

        return results
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """
        Get information about a specific collection.
        
        Returns:
            Dict with collection details or error message.
        """
        return self.manager.get_collection_info(collection_name)