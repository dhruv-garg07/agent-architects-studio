import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import chromadb


class ChromaCollectionManager:
    def __init__(self):
        # Load env vars
        load_dotenv()
        self.api_key = os.getenv("CHROMA_API_KEY")
        self.tenant = os.getenv("CHROMA_TENANT")
        self.database = os.getenv("CHROMA_DATABASE")

        # Connect to Chroma Cloud
        self.client = chromadb.CloudClient(
            api_key=self.api_key,
            tenant=self.tenant,
            database=self.database
        )

    def list_collections(self) -> List[str]:
        """Return a list of existing collection names."""
        return [col.name for col in self.client.list_collections()]

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

        Args:
            collection_name (str): Name of the new collection.
            ids (list of str, optional): Unique IDs for the documents.
            documents (list of str, optional): Text documents to store.
            metadatas (list of dict, optional): Metadata for documents.

        Returns:
            str: Message about collection creation and data addition.
        """
        existing_collections = self.list_collections()

        if collection_name in existing_collections:
            return f"⚠️ Collection '{collection_name}' already exists."

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
