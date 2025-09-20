import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import chromadb


class ChromaReader:
    def __init__(self):
        # Load env variables
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

    def get_collection(self, collection_name: str):
        """Return a collection object from ChromaDB."""
        return self.client.get_or_create_collection(name=collection_name)

    def search(
        self,
        collection_name: str,
        query: str,
        n_results: int = 3,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Perform a search in a given collection.
        """
        collection = self.get_collection(collection_name)

        query_args = {
            "query_texts": [query],
            "n_results": n_results
        }

        if metadata_filter:  # only add if not None/empty
            query_args["where"] = metadata_filter

        results = collection.query(**query_args)

        output = []
        for doc, metadata, doc_id in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["ids"][0]
        ):
            output.append({
                "id": doc_id,
                "document": doc,
                "metadata": metadata
            })

        return output
