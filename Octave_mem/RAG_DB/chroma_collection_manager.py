import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import chromadb

# Load environment variables
load_dotenv()

# GLOBAL singleton CloudClient for performance
CHROMA_CLIENT = chromadb.CloudClient(
    api_key=os.getenv("CHROMA_API_KEY"),
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
)

class ChromaCollectionManager:
    """
    Optimized version:
    - Caches collection objects in memory
    - Avoids repeated server calls for existence checks
    - Reduces expensive metadata lookups
    """

    _collection_cache: Dict[str, any] = {}  # shared cache across all instances

    def __init__(self, database=None):
        self.client = CHROMA_CLIENT
        self.database = database or os.getenv("CHROMA_DATABASE_CHAT_HISTORY")

    # -----------------------------
    # Utility / Internal Helpers
    # -----------------------------

    def _get_or_cache(self, collection_name: str):
        """Get collection from cache or server."""
        if collection_name not in self._collection_cache:
            try:
                col = self.client.get_or_create_collection(name=collection_name)
                self._collection_cache[collection_name] = col
            except Exception as e:
                print(f"Error loading collection {collection_name}: {e}")
                return None
        return self._collection_cache[collection_name]

    # -----------------------------
    # Collection Operations
    # -----------------------------

    def list_collections(self) -> List[str]:
        """Return a list of collection names."""
        try:
            return [c.name for c in self.client.list_collections()]
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            self.client.get_collection(collection_name)
            return True
        except:
            return False

    def get_collection(self, collection_name: str):
        """Return a cached or loaded collection."""
        return self._get_or_cache(collection_name)

    def create_collection(self, collection_name: str, ids=None, documents=None, metadatas=None) -> str:
        """Create a new collection and optionally add data."""
        if self.collection_exists(collection_name):
            return f"⚠️ Collection '{collection_name}' already exists."

        try:
            col = self.client.create_collection(name=collection_name)
            self._collection_cache[collection_name] = col  # cache it

            # Add initial data if provided
            if ids and documents:
                col.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas or [{} for _ in ids]
                )
                return f"✅ Collection '{collection_name}' created with {len(ids)} documents."

            return f"✅ Empty collection '{collection_name}' created."

        except Exception as e:
            return f"❌ Error creating '{collection_name}': {e}"

    def create_or_update_collection(self, collection_name: str, ids=None, documents=None, metadatas=None) -> str:
        """Create collection if missing, otherwise upsert into it."""
        if not ids or not documents:
            return "⚠️ ids and documents required."

        try:
            col = self._get_or_cache(collection_name)
            action = "updated" if self.collection_exists(collection_name) else "created"

            col.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas or [{} for _ in ids]
            )
            return f"✅ Collection '{collection_name}' {action} with {len(ids)} items."

        except Exception as e:
            return f"❌ Error updating '{collection_name}': {e}"

    def update_collection(self, collection_name: str, ids, documents, metadatas=None) -> str:
        """Upsert documents into collection."""
        col = self.get_collection(collection_name)
        if not col:
            return f"⚠️ Collection '{collection_name}' does not exist."

        try:
            col.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas or [{} for _ in ids]
            )
            return f"✅ Updated {len(ids)} documents in '{collection_name}'."
        except Exception as e:
            return f"❌ Error updating '{collection_name}': {e}"

    def update_collection_metadata(self, collection_name, ids, metadatas) -> str:
        """Update metadata only."""
        col = self.get_collection(collection_name)
        if not col:
            return f"⚠️ Collection '{collection_name}' does not exist."

        try:
            col.upsert(ids=ids, documents=[None] * len(ids), metadatas=metadatas)
            return f"✅ Metadata updated for {len(ids)} items in '{collection_name}'."
        except Exception as e:
            return f"❌ Error updating metadata: {e}"

    def replace_collection(self, collection_name, ids=None, documents=None, metadatas=None) -> str:
        """Delete + recreate collection."""
        try:
            if self.collection_exists(collection_name):
                self.client.delete_collection(collection_name)
                self._collection_cache.pop(collection_name, None)

            col = self.client.create_collection(name=collection_name)
            self._collection_cache[collection_name] = col

            if ids and documents:
                col.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas or [{} for _ in ids]
                )
                return f"✅ Collection '{collection_name}' replaced with {len(ids)} documents."

            return f"✅ Collection '{collection_name}' replaced (empty)."

        except Exception as e:
            return f"❌ Error replacing '{collection_name}': {e}"

    def delete_collection(self, collection_name: str) -> str:
        """Delete a collection."""
        try:
            if not self.collection_exists(collection_name):
                return f"⚠️ Collection '{collection_name}' does not exist."

            self.client.delete_collection(collection_name)
            self._collection_cache.pop(collection_name, None)
            return f"✅ Deleted collection '{collection_name}'."
        except Exception as e:
            return f"❌ Error deleting collection: {e}"

    # -----------------------------
    # Document Operations
    # -----------------------------

    def delete_documents(self, collection_name: str, ids: List[str]) -> str:
        """Delete specific documents."""
        col = self.get_collection(collection_name)
        if not col:
            return f"⚠️ Collection '{collection_name}' does not exist."

        try:
            col.delete(ids=ids)
            return f"✅ Deleted {len(ids)} documents from '{collection_name}'."
        except Exception as e:
            return f"❌ Error deleting documents: {e}"

    def get_collection_info(self, collection_name: str) -> Dict:
        """Return collection statistics."""
        col = self.get_collection(collection_name)
        if not col:
            return {"error": f"Collection '{collection_name}' does not exist."}

        try:
            return {
                "name": collection_name,
                "document_count": col.count(),
                "exists": True
            }
        except Exception as e:
            return {"error": str(e)}

    def verify_data_in_collection(self, collection_name: str, expected_ids=None) -> Dict:
        """Verify stored data and optionally compare with expected IDs."""
        col = self.get_collection(collection_name)
        if not col:
            return {"error": f"Collection '{collection_name}' does not exist."}

        try:
            results = col.get()
            actual_ids = results.get("ids", [])

            data = {
                "collection": collection_name,
                "document_count": len(actual_ids),
                "actual_ids": actual_ids,
                "documents": results.get("documents", []),
                "metadatas": results.get("metadatas", [])
            }

            if expected_ids:
                data["expected_ids"] = expected_ids
                data["ids_match"] = set(actual_ids) == set(expected_ids)

            return data

        except Exception as e:
            return {"error": str(e)}
