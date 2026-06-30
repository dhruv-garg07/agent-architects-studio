"""
GitMem v2.0 — Embedder

Generates vector embeddings for memory content.
Designed to be pluggable (OpenAI, HuggingFace, local models, etc.).

Priority order:
  1. OpenAI API  — if OPENAI_API_KEY is set.
  2. Deterministic random unit-vectors  — stable per-text fallback so that
     cosine-similarity is at least meaningful (identical texts get identical
     vectors) even when no API key is available.  Better than all-zeros,
     which makes every similarity score undefined / zero.
"""

from typing import List
import os
import math
import random


class Embedder:
    """Generates vector embeddings for agent memory content."""

    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small"):
        self.provider = provider
        self.model = model
        # Load API keys from environment
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._dim = 1536  # matches text-embedding-3-small / ada-002 output dimension

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed(self, text: str) -> List[float]:
        """Generate an embedding for a single string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of strings.

        Returns a list of float vectors.  Tries OpenAI first; falls back to
        deterministic random unit-vectors when no API key is configured or
        when the API call fails.
        """
        if not texts:
            return []

        # ── Attempt 1: Real OpenAI embeddings ────────────────────────
        if self.api_key:
            try:
                import openai  # optional dependency; may not be installed
                client = openai.OpenAI(api_key=self.api_key)
                response = client.embeddings.create(input=texts, model=self.model)
                return [item.embedding for item in response.data]
            except ImportError:
                print("[Embedder] 'openai' package not installed. "
                      "Run `pip install openai` to enable real embeddings.")
            except Exception as exc:
                print(f"[Embedder] OpenAI embedding call failed: {exc}. "
                      "Falling back to deterministic random vectors.")

        # ── Fallback: deterministic unit-vectors ──────────────────────
        # Each text maps to a unique, stable unit vector derived from its
        # content hash.  This means:
        #   - Identical texts always get the same vector.
        #   - Different texts get different vectors (with high probability).
        #   - Cosine similarity is well-defined (vectors are non-zero).
        # This is much better than all-zero vectors but is NOT semantically
        # meaningful — replace with real embeddings for production use.
        return [self._deterministic_unit_vector(text) for text in texts]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _deterministic_unit_vector(self, text: str) -> List[float]:
        """Return a stable, normalised random vector seeded by the text hash."""
        seed = hash(text) & 0xFFFF_FFFF  # keep positive 32-bit seed
        rng = random.Random(seed)
        vec = [rng.gauss(0.0, 1.0) for _ in range(self._dim)]
        magnitude = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / magnitude for v in vec]
