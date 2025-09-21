import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from RAG_DB.chroma_collection_manager import ChromaCollectionManager

class ChromaCollectionWrapper:
    def __init__(self):
        """Initialize the wrapper with ChromaCollectionManager."""
        load_dotenv()
        self.manager = ChromaCollectionManager()
    
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
        Perform multiple operations with verification.
        
        Args:
            operations: List of operation dictionaries with keys:
                - type: "create_or_update", "update", or "replace"
                - collection_name: str
                - ids: List[str]
                - documents: List[str]
                - metadatas: Optional[List[Dict]]
        
        Returns:
            List of results with verification for each operation.
        """
        results = []
        
        for op in operations:
            op_type = op.get("type")
            collection_name = op.get("collection_name")
            ids = op.get("ids")
            documents = op.get("documents")
            metadatas = op.get("metadatas")
            
            if op_type == "create_or_update":
                result = self.create_or_update_collection_with_verify(
                    collection_name, ids, documents, metadatas
                )
            elif op_type == "update":
                result = self.update_collection_with_verify(
                    collection_name, ids, documents, metadatas
                )
            elif op_type == "replace":
                result = self.replace_collection_with_verify(
                    collection_name, ids, documents, metadatas
                )
            else:
                result = {
                    "operation": "unknown",
                    "result": f"Unknown operation type: {op_type}",
                    "verification": {"error": f"Unknown operation type: {op_type}"},
                    "success": False
                }
            
            results.append(result)
        
        return results