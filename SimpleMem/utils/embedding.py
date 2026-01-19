"""
Embedding utilities - Generate vector embeddings using a remote embedding API by default
This avoids downloading large models locally. The public method names are kept the same
for backward compatibility (encode, encode_single, encode_query, encode_documents).
"""
from typing import List, Optional, Dict, Any
import numpy as np
from SimpleMem.config_loader import EMBEDDING_MODEL, REMOTE_EMBEDDING_URL, REMOTE_EMBEDDING_DIMENSION
import os
import requests
import json


class EmbeddingModel:
    """
    Embedding model that calls a remote embedding API to generate vectors.
    This class preserves the same public API as the original implementation.
    """
    def __init__(self, model_name: str = None, use_optimization: bool = True):
        self.model_name = model_name or EMBEDDING_MODEL
        self.use_optimization = use_optimization

        print(f"Using remote embedding API (no local download): {REMOTE_EMBEDDING_URL or 'unknown'}")
        # Use remote embedding API by default
        self.model_type = "remote_api"
        self.dimension = REMOTE_EMBEDDING_DIMENSION
        self.supports_query_prompt = False

    def encode(self, texts: List[str], is_query: bool = False) -> np.ndarray:
        """
        Encode list of texts by calling the remote embedding API for each text.

        Args:
        - texts: List of texts to encode
        - is_query: Ignored for remote API (kept for compatibility)
        """
        if isinstance(texts, str):
            texts = [texts]

        # The remote API does not support a separate query prompt, so use standard encoding
        return self._encode_standard(texts)

    def encode_single(self, text: str, is_query: bool = False) -> np.ndarray:
        """
        Encode single text
        """
        return self.encode([text], is_query=is_query)[0]

    def encode_query(self, queries: List[str]) -> np.ndarray:
        """
        Encode queries (kept for API compatibility)
        """
        return self.encode(queries, is_query=True)

    def encode_documents(self, documents: List[str]) -> np.ndarray:
        """
        Encode documents (kept for API compatibility)
        """
        return self.encode(documents, is_query=False)

    def _call_remote_embed_single(self, text: str, timeout: int = 60) -> np.ndarray:
        """
        Call the remote embedding API for a single text and return a normalized numpy array.

        This method follows the test flow:
          1) POST to BASE_URL with payload {"data": [text]} and read event_id
          2) GET streaming endpoint at BASE_URL/{event_id} and parse lines starting with 'data:'
          3) Extract 'dense_embedding' from the JSON payload

        Raises on HTTP errors or if no embedding data is returned.
        """
        base_url = getattr(config, "REMOTE_EMBEDDING_URL", None)
        if not base_url:
            raise RuntimeError("REMOTE_EMBEDDING_URL not configured in config.py")

        payload = {"data": [text]}
        try:
            resp = requests.post(base_url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"Failed to POST to remote embed API: {e}")
            raise

        data = resp.json()
        event_id = data.get("event_id") or data.get("hash")
        if not event_id:
            # Some endpoints may return the embedding immediately in 'data' key
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                # try to parse returned structure
                try:
                    d = data["data"]
                    if len(d) and isinstance(d[0], dict) and "dense_embedding" in d[0]:
                        emb = np.array(d[0]["dense_embedding"], dtype=np.float32)
                        norm = np.linalg.norm(emb)
                        if norm > 0:
                            emb = emb / norm
                        return emb
                except Exception:
                    pass

            raise ValueError("No event_id returned by remote embedding API")

        stream_url = f"{base_url}/{event_id}"

        try:
            with requests.get(stream_url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                embedding = None
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    line = line.strip()
                    # Lines may be like: 'event: complete' or 'data: [{...}]'
                    if line.startswith("data:"):
                        payload_text = line[len("data:"):].strip()
                        try:
                            parsed = json.loads(payload_text)
                        except Exception:
                            # some servers prefix additional characters; try to find first '['
                            try:
                                idx = payload_text.index("[")
                                parsed = json.loads(payload_text[idx:])
                            except Exception:
                                parsed = None

                        if parsed:
                            # Expect parsed to be a list of dicts
                            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                                entry = parsed[0]
                                if "dense_embedding" in entry:
                                    embedding = entry["dense_embedding"]
                                    break
                    # Some implementations send the final payload under 'event: complete' line without 'data:'
                    if line.startswith("event: complete"):
                        continue

                if embedding is None:
                    raise ValueError("No embedding found in streaming response")

                emb = np.array(embedding, dtype=np.float32)
                # Update dimension dynamically based on returned embedding length
                try:
                    if not hasattr(self, 'dimension') or self.dimension != emb.shape[0]:
                        self.dimension = emb.shape[0]
                        print(f"Detected remote embedding dimension: {self.dimension}")
                except Exception:
                    pass

                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                return emb
        except Exception as e:
            print(f"Error while streaming embedding: {e}")
            raise

    def _encode_standard(self, texts: List[str]) -> np.ndarray:
        """Encode texts using the remote API for each item and return a numpy array"""
        embeddings = []
        for t in texts:
            emb = self._call_remote_embed_single(t)
            embeddings.append(emb)

        # Stack to (N, D)
        try:
            arr = np.stack(embeddings, axis=0)
        except Exception as e:
            print(f"Failed to stack embeddings: {e}")
            raise
        return arr

