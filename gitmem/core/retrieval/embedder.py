"""
GitMem v2.0 — Embedder

Generates vector embeddings for memory content.
Designed to be pluggable (OpenAI, local models, etc.).
"""

from typing import List, Union
import os


class Embedder:
    """Generates vector embeddings."""
    
    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        self.provider = provider
        self.model = model
        # Try to load API keys
        self.api_key = os.getenv("OPENAI_API_KEY")

    def embed(self, text: str) -> List[float]:
        """Generate an embedding for a single string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of strings.
        Returns a list of float vectors.
        """
        if not texts:
            return []
            
        # Stub implementation for v2.0 architecture.
        # In a real system, this would call OpenAI/Cohere API or local SentenceTransformers.
        
        # Fake an embedding for now (dim 1536 for OpenAI compat)
        dim = 1536
        fake_vector = [0.0] * dim
        return [fake_vector for _ in texts]
