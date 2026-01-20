import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import chromadb
import httpx
import logging
import requests, json
# -------------------------------------------------
# Environment & Logging
# -------------------------------------------------

load_dotenv()

logging.basicConfig(level=logging.ERROR)

# -------------------------------------------------
# Remote Embedding Configuration
# -------------------------------------------------

REMOTE_EMBEDDING_URL = os.getenv("REMOTE_EMBEDDING_URL")
REMOTE_EMBEDDING_DIMENSION = int(os.getenv("REMOTE_EMBEDDING_DIMENSION", "768"))

if not REMOTE_EMBEDDING_URL:
    raise RuntimeError("REMOTE_EMBEDDING_URL must be set")

# -------------------------------------------------
# Remote Embedding Client
# -------------------------------------------------

class RemoteEmbeddingClient:
    """
    Stateless remote embedding client.
    Chroma never sees text → only vectors.
    """

    def __init__(self, url: str):
        self.url = url
        self.http = httpx.Client(timeout=60)

    
    REMOTE_EMBEDDING_URL = "https://iotacluster-embedding-model.hf.space/gradio_api/call/embed_dense"

class RemoteEmbeddingClient:
    """
    Stateless remote embedding client.
    HF Space = single-text embedding → loop safely.
    """

    def __init__(self, url: str):
        self.url = url

    def _embed_one(self, text: str, timeout: int = 60) -> List[float]:
        # Step 1: POST
        resp = requests.post(
            self.url,
            json={"data": [text]},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()

        event_id = resp.json().get("event_id")
        if not event_id:
            raise RuntimeError("No event_id returned from embedding service")

        # Step 2: Stream
        stream_url = f"{self.url}/{event_id}"

        with requests.get(stream_url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("data:"):
                    payload = json.loads(line.replace("data:", "").strip())
                    return payload[0]["dense_embedding"]

        raise RuntimeError("Embedding stream ended without result")

    def embed_remote(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts safely (one-by-one).
        """
        embeddings = []

        for idx, text in enumerate(texts):
            vec = self._embed_one(text)
            embeddings.append(vec)

        return embeddings


# -------------------------------------------------
# Global Chroma Cloud Client (NO EMBEDDING FUNCTION)
# -------------------------------------------------

CHROMA_CLIENT = chromadb.CloudClient(
    api_key=os.getenv("CHROMA_API_KEY"),
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"),
)

# -------------------------------------------------
# Chroma Collection Manager (Remote Embeddings)
# -------------------------------------------------

class ChromaCollectionManager:
    """
    Cloud-only, embedding-free Chroma manager.
    All embeddings are generated remotely.
    """

    _collection_cache: Dict[str, any] = {}

    def __init__(self, database: Optional[str] = None):
        self.client = CHROMA_CLIENT
        self.database = database or os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        self.embedder = RemoteEmbeddingClient(REMOTE_EMBEDDING_URL)

    # -------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------

    def _get_or_cache(self, collection_name: str):
        if collection_name not in self._collection_cache:
            col = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=None  # 🚫 NEVER let Chroma embed
            )
            self._collection_cache[collection_name] = col
        return self._collection_cache[collection_name]

    # -------------------------------------------------
    # Collection Ops
    # -------------------------------------------------

    def list_collections(self) -> List[str]:
        return [c.name for c in self.client.list_collections()]

    def collection_exists(self, collection_name: str) -> bool:
        try:
            self.client.get_collection(collection_name)
            return True
        except:
            return False

    def get_collection(self, collection_name: str):
        return self._get_or_cache(collection_name)

    def create_collection(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> str:

        if self.collection_exists(collection_name):
            return f"⚠️ Collection '{collection_name}' already exists."

        col = self.client.create_collection(
            name=collection_name,
            embedding_function=None
        )
        self._collection_cache[collection_name] = col

        if ids and documents:
            embeddings = self.embedder.embed(documents)
            col.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{} for _ in ids],
            )
            return f"✅ Collection '{collection_name}' created with {len(ids)} docs."

        return f"✅ Empty collection '{collection_name}' created."

    def create_or_update_collection(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
    ) -> str:

        col = self._get_or_cache(collection_name)
        embeddings = self.embedder.embed_remote(documents)

        col.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{} for _ in ids],
        )

        return f"✅ Collection '{collection_name}' upserted ({len(ids)} items)."

    def replace_collection(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> str:

        if self.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            self._collection_cache.pop(collection_name, None)

        col = self.client.create_collection(
            name=collection_name,
            embedding_function=None
        )
        self._collection_cache[collection_name] = col

        if ids and documents:
            embeddings = self.embedder.embed(documents)
            col.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{} for _ in ids],
            )
            return f"✅ Collection '{collection_name}' replaced with {len(ids)} docs."

        return f"✅ Collection '{collection_name}' replaced (empty)."

    def delete_collection(self, collection_name: str) -> str:
        self.client.delete_collection(collection_name)
        self._collection_cache.pop(collection_name, None)
        return f"✅ Deleted collection '{collection_name}'."

    # -------------------------------------------------
    # Document Ops
    # -------------------------------------------------

    def delete_documents(self, collection_name: str, ids: List[str]) -> str:
        col = self.get_collection(collection_name)
        col.delete(ids=ids)
        return f"✅ Deleted {len(ids)} documents."

    def query_collection(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> Dict:

        col = self.get_collection(collection_name)
        query_embeddings = self.embedder.embed(query_texts)

        return col.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
        )

    def get_collection_info(self, collection_name: str) -> Dict:
        col = self.get_collection(collection_name)
        return {
            "name": collection_name,
            "document_count": col.count(),
            "exists": True,
        }

    def verify_data_in_collection(
        self,
        collection_name: str,
        expected_ids: Optional[List[str]] = None,
    ) -> Dict:

        col = self.get_collection(collection_name)
        results = col.get()

        actual_ids = results.get("ids", [])

        data = {
            "collection": collection_name,
            "document_count": len(actual_ids),
            "actual_ids": actual_ids,
            "documents": results.get("documents", []),
            "metadatas": results.get("metadatas", []),
        }

        if expected_ids is not None:
            data["expected_ids"] = expected_ids
            data["ids_match"] = set(actual_ids) == set(expected_ids)

        return data


if __name__ == "__main__":
    print("🚀 Running Chroma Remote Embedding Smoke Test")

    manager = ChromaCollectionManager()

    COLLECTION = "remote_embedding_test"

    ids = ["doc1", "doc2"]
    docs = [
        "Chroma is a vector database for AI applications.",
        "Remote embeddings allow scalable inference without local GPUs."
    ]
    metadatas = [
        {"source": "test", "idx": 1},
        {"source": "test", "idx": 2},
    ]

    print("\n📦 Creating / Updating collection...")
    print(
        manager.create_or_update_collection(
            collection_name=COLLECTION,
            ids=ids,
            documents=docs,
            metadatas=metadatas,
        )
    )

    print("\n🔍 Verifying stored data...")
    print(manager.verify_data_in_collection(COLLECTION, expected_ids=ids))

    print("\n📊 Collection info...")
    print(manager.get_collection_info(COLLECTION))

    print("\n🧹 Cleaning up...")
    print(manager.delete_collection(COLLECTION))

    print("\n✅ Test completed successfully")
