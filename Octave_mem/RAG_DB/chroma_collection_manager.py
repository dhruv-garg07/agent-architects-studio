import os
from typing import List, Dict, Optional, Union
from dotenv import load_dotenv
import chromadb

class ChromaCollectionManager:
    def __init__(self, database: str = None):
        # Load env vars
        load_dotenv()
        self.api_key = os.getenv("CHROMA_API_KEY")
        self.tenant = os.getenv("CHROMA_TENANT")

        # Use provided database or fallback to env var
        if database is None:
            self.database = os.getenv("CHROMA_DATABASE")
        else:
            self.database = database
        print(f"Using Chroma Database: {self.database}")
        # Connect to Chroma Cloud
        self.client = chromadb.CloudClient(
            api_key=self.api_key,
            tenant=self.tenant,
            database=self.database
        )

    def list_collections(self) -> List[str]:
        """Return a list of existing collection names."""
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists by trying to get it."""
        try:
            self.client.get_collection(collection_name)
            return True
        except:
            return False

    def get_collection(self, collection_name: str):
        """Get a collection instance."""
        try:
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"Error getting collection {collection_name}: {e}")
            return None

    def create_collection(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> str:
        """
        Create a new collection (only if it does not exist).
        Optionally add data into it.
        """
        if self.collection_exists(collection_name):
            return f"⚠️ Collection '{collection_name}' already exists."

        try:
            # Create the new collection
            collection = self.client.create_collection(name=collection_name)

            # Optionally add data
            if ids and documents:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas if metadatas else [{} for _ in ids]
                )
                return f"✅ Collection '{collection_name}' created and {len(ids)} documents added."
            
            return f"✅ Empty collection '{collection_name}' created."

        except Exception as e:
            return f"❌ Error creating collection '{collection_name}': {str(e)}"

    def create_or_update_collection(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> str:
        """
        Create a new collection or update existing one with new documents.
        Uses upsert to update existing documents or add new ones.
        """
        if not ids or not documents:
            return "⚠️ Both ids and documents are required for update operations."

        try:
            # Check if collection exists
            if self.collection_exists(collection_name):
                collection = self.get_collection(collection_name)
                action = "updated"
            else:
                collection = self.client.create_collection(name=collection_name)
                action = "created"

            # Upsert documents (update existing or add new)
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas if metadatas else [{} for _ in ids]
            )
            
            return f"✅ Collection '{collection_name}' {action} with {len(ids)} documents."

        except Exception as e:
            return f"❌ Error processing collection '{collection_name}': {str(e)}"

    def update_collection(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None
    ) -> str:
        """
        Add new documents to an existing collection using upsert.
        """
        if not self.collection_exists(collection_name):
            return f"⚠️ Collection '{collection_name}' does not exist."

        try:
            collection = self.get_collection(collection_name)
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas if metadatas else [{} for _ in ids]
            )
            return f"✅ Added/updated {len(ids)} documents in collection '{collection_name}'."

        except Exception as e:
            return f"❌ Error updating collection '{collection_name}': {str(e)}"
    
    def update_collection_metadata(
        self,
        collection_name: str,
        ids: List[str],
        metadatas: List[Dict]
    ) -> str:
        """
        Update metadata in an existing collection.
        """
        if not self.collection_exists(collection_name):
            return f"⚠️ Collection '{collection_name}' does not exist."

        try:
            collection = self.get_collection(collection_name)
            collection.upsert(
                ids=ids,
                documents=None,  # Don't update documents
                metadatas=metadatas
            )
            return f"✅ Updated metadata for {len(ids)} documents in collection '{collection_name}'."

        except Exception as e:
            return f"❌ Error updating metadata in collection '{collection_name}': {str(e)}"

    def replace_collection(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None
    ) -> str:
        """
        Replace entire collection content by deleting and recreating it.
        """
        try:
            # Delete existing collection if it exists
            if self.collection_exists(collection_name):
                self.client.delete_collection(collection_name)

            # Create new collection
            collection = self.client.create_collection(name=collection_name)

            # Add data if provided
            if ids and documents:
                collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas if metadatas else [{} for _ in ids]
                )
                return f"✅ Collection '{collection_name}' replaced with {len(ids)} documents."

            return f"✅ Collection '{collection_name}' replaced (now empty)."

        except Exception as e:
            return f"❌ Error replacing collection '{collection_name}': {str(e)}"

    def delete_collection(self, collection_name: str) -> str:
        """
        Delete a collection.
        """
        if not self.collection_exists(collection_name):
            return f"⚠️ Collection '{collection_name}' does not exist."

        try:
            self.client.delete_collection(collection_name)
            return f"✅ Collection '{collection_name}' deleted successfully."
        except Exception as e:
            return f"❌ Error deleting collection '{collection_name}': {str(e)}"

    # To get information about a collection.
    def get_collection_info(self, collection_name: str) -> Dict:
        """
        Get information about a collection.
        """
        if not self.collection_exists(collection_name):
            return {"error": f"Collection '{collection_name}' does not exist."}

        try:
            collection = self.get_collection(collection_name)
            count = collection.count()
            return {
                "name": collection_name,
                "document_count": count,
                "exists": True
            }
        except Exception as e:
            return {"error": f"Error getting info for '{collection_name}': {str(e)}"}

    # To verify the data that was added in a collection.
    def verify_data_in_collection(
        self,
        collection_name: str,
        expected_ids: List[str] = None
    ) -> Dict:
        """
        Verify that data was actually added to the collection.
        """
        if not self.collection_exists(collection_name):
            return {"error": f"Collection '{collection_name}' does not exist."}

        try:
            collection = self.get_collection(collection_name)
            
            # Get all documents
            results = collection.get()
            
            actual_ids = results['ids'] if results and 'ids' in results else []
            document_count = len(actual_ids)
            
            verification = {
                "collection": collection_name,
                "document_count": document_count,
                "actual_ids": actual_ids,
                "documents": results['documents'] if results and 'documents' in results else [],
                "metadatas": results['metadatas'] if results and 'metadatas' in results else []
            }
            
            if expected_ids:
                verification["expected_ids"] = expected_ids
                verification["ids_match"] = set(actual_ids) == set(expected_ids)
            
            return verification
            
        except Exception as e:
            return {"error": f"Error verifying data in '{collection_name}': {str(e)}"}