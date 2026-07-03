import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import chromadb
import logging
import numpy as np
import threading

# -------------------------------------------------
# Environment & Logging
# -------------------------------------------------

load_dotenv(override=True)

logging.basicConfig(level=logging.ERROR)

# -------------------------------------------------
# Remote Embedding Configuration
# -------------------------------------------------
from chromadb.api.types import EmbeddingFunction
class DisabledEmbeddingFunction(EmbeddingFunction):
    """
    Hard-disable Chroma local embeddings.
    If Chroma ever tries to embed, crash immediately.
    """

    def __call__(self, texts):
        raise RuntimeError(
            "[ERROR] Local embeddings are disabled. "
            "Remote embeddings must be provided explicitly."
        )

# HF Inference API config
# HF Inference API config
HF_TOKEN = os.getenv("HF_TOKEN")
HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
REMOTE_EMBEDDING_DIMENSION = int(os.getenv("REMOTE_EMBEDDING_DIMENSION", "384"))

# Keep REMOTE_EMBEDDING_URL for backward compat but it is no longer required
REMOTE_EMBEDDING_URL = os.getenv("REMOTE_EMBEDDING_URL", "hf-inference")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN must be set in environment variables")

# -------------------------------------------------
# Remote Embedding Client (HuggingFace Inference API)
# -------------------------------------------------

class RemoteEmbeddingClient:
    """
    Embedding client using HuggingFace Inference API.
    Uses huggingface_hub InferenceClient for feature_extraction.
    No dependency on HF Spaces — uses the official Inference API directly.
    """
    _embedding_cache = {}
    _cache_lock = threading.Lock()

    def __init__(self, model: str = None, api_key: str = None):
        from huggingface_hub import InferenceClient
        self.model = model or HF_EMBEDDING_MODEL
        self.api_key = api_key or HF_TOKEN
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=self.api_key,
        )
        print(f"[RemoteEmbeddingClient] Initialized with model: {self.model}")

    def _embed_one(self, text: str) -> List[float]:
        """Embed a single text using HF Inference API."""
        result = self.client.feature_extraction(
            text,
            model=self.model,
        )
        # result is a numpy array — convert to list
        vec = np.array(result).flatten().tolist()
        return vec

    def embed_remote(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts safely (one-by-one with retries), caching results.
        """
        import time
        embeddings = [None] * len(texts)
        missing_texts = []
        missing_indices = []

        with self._cache_lock:
            for idx, text in enumerate(texts):
                if text in self._embedding_cache:
                    embeddings[idx] = self._embedding_cache[text]
                else:
                    missing_texts.append(text)
                    missing_indices.append(idx)

        if missing_texts:
            max_retries = 3
            for idx_in_missing, text in enumerate(missing_texts):
                orig_idx = missing_indices[idx_in_missing]
                for attempt in range(max_retries):
                    try:
                        vec = self._embed_one(text)
                        with self._cache_lock:
                            self._embedding_cache[text] = vec
                        embeddings[orig_idx] = vec
                        break  # Success
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"[WARNING] Embedding failed for text {orig_idx} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in 2 seconds...")
                            time.sleep(2)
                        else:
                            raise RuntimeError(f"Failed to embed text after {max_retries} attempts: {e}")

        return embeddings

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Conform to chromadb EmbeddingFunction protocol."""
        return self.embed_remote(input)

    def name(self) -> str:
        return "RemoteEmbeddingClient"


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
        self.embedder = RemoteEmbeddingClient()

        # [SUCCESS] SINGLE shared disabled embedding function
        self._disabled_ef = DisabledEmbeddingFunction()

    # -------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------


    def _get_or_cache(self, collection_name: str):
        if collection_name not in self._collection_cache:
            # First, try to get existing collection (without specifying embedding function)
            # This prevents conflicts with collections created with different embedding functions
            try:
                col = self.client.get_collection(name=collection_name)
                print(f"[ChromaCollectionManager] Got existing collection: {collection_name}")
            except Exception:
                # Collection doesn't exist, create it with our embedding function
                col = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self._disabled_ef,
                    metadata={"embedding": "remote-only"},
                )
                print(f"[ChromaCollectionManager] Created new collection: {collection_name}")
            
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
            return f"[WARNING] Collection '{collection_name}' already exists."

        col = self.client.create_collection(
            name=collection_name,

            # [HOT] SAME FIX HERE
            embedding_function=self._disabled_ef,
            metadata={"embedding": "remote-only"},
        )
        self._collection_cache[collection_name] = col

        if ids and documents:
            embeddings = self.embedder.embed_remote(documents)

            # [SUCCESS] SAFETY CHECK
            if len(embeddings) != len(ids):
                raise ValueError("Embedding count mismatch")

            col.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{} for _ in ids],
            )
            return f"[SUCCESS] Collection '{collection_name}' created with {len(ids)} docs."

        return f"[SUCCESS] Empty collection '{collection_name}' created."

    def create_or_update_collection(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
    ) -> str:

        col = self._get_or_cache(collection_name)
        embeddings = self.embedder.embed_remote(documents)

        # [SUCCESS] HARD VALIDATION (prevents silent bugs)
        if len(embeddings) != len(ids):
            raise ValueError(
                f"Embedding count mismatch: {len(embeddings)} vs {len(ids)}"
            )

        col.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{} for _ in ids],
        )

        return f"[SUCCESS] Collection '{collection_name}' upserted ({len(ids)} items)."

    
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

            # [HOT] SAME FIX
            embedding_function=self._disabled_ef,
            metadata={"embedding": "remote-only"},
        )
        self._collection_cache[collection_name] = col

        if ids and documents:
            embeddings = self.embedder.embed_remote(documents)

            if len(embeddings) != len(ids):
                raise ValueError("Embedding count mismatch")

            col.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{} for _ in ids],
            )
            return f"[SUCCESS] Collection '{collection_name}' replaced with {len(ids)} docs."

        return f"[SUCCESS] Collection '{collection_name}' replaced (empty)."

    def delete_collection(self, collection_name: str) -> str:
        self.client.delete_collection(collection_name)
        self._collection_cache.pop(collection_name, None)
        return f"[SUCCESS] Deleted collection '{collection_name}'."

    # -------------------------------------------------
    # Document Ops
    # -------------------------------------------------

    def delete_documents(self, collection_name: str, ids: List[str]) -> str:
        col = self.get_collection(collection_name)
        col.delete(ids=ids)
        return f"[SUCCESS] Deleted {len(ids)} documents."

    def query_collection(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> Dict:

        col = self.get_collection(collection_name)
        query_embeddings = self.embedder.embed_remote(query_texts)

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
            data["ids_match"] = set(expected_ids).issubset(set(actual_ids))

        return data

# import os
# from dotenv import load_dotenv
# import chromadb

# # Load env
# load_dotenv()

# client = chromadb.CloudClient(
#     api_key=os.getenv("CHROMA_API_KEY"),
#     tenant=os.getenv("CHROMA_TENANT"),
#     database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY"),
# )

# def delete_all_collections():
#     collections = client.list_collections()

#     if not collections:
#         print("[SUCCESS] No collections found. Nothing to delete.")
#         return

#     print(f"[HOT] Deleting {len(collections)} collections...\n")

#     for c in collections:
#         try:
#             print(f"[DELETE] Deleting collection: {c.name}")
#             client.delete_collection(c.name)
#         except Exception as e:
#             print(f"[ERROR] Failed to delete {c.name}: {e}")

#     print("\n[SUCCESS] ALL collections deleted successfully.")

# if __name__ == "__main__":
#     confirm = input("[WARNING] Type DELETE-ALL to confirm: ")
#     if confirm == "DELETE-ALL":
#         delete_all_collections()
#     else:
#         print("[ERROR] Aborted. No collections were deleted.")

# if __name__ == "__main__":
#     print("[START] Running Chroma Remote Embedding Smoke Test")

#     manager = ChromaCollectionManager()

#     COLLECTION = "remote_embedding_test"

#     ids = ["doc1", "doc2"]
#     docs = [
#         "Chroma is a vector database for AI applications.",
#         "Remote embeddings allow scalable inference without local GPUs."
#     ]
#     metadatas = [
#         {"source": "test", "idx": 1},
#         {"source": "test", "idx": 2},
#     ]

#     print("\n[PACKAGE] Creating / Updating collection...")
#     print(
#         manager.create_or_update_collection(
#             collection_name=COLLECTION,
#             ids=ids,
#             documents=docs,
#             metadatas=metadatas,
#         )
#     )

#     print("\n[SEARCH] Verifying stored data...")
#     print(manager.verify_data_in_collection(COLLECTION, expected_ids=ids))

#     print("\n[STATS] Collection info...")
#     print(manager.get_collection_info(COLLECTION))

#     print("\n[CLEAN] Cleaning up...")
#     print(manager.delete_collection(COLLECTION))

#     print("\n[SUCCESS] Test completed successfully")
