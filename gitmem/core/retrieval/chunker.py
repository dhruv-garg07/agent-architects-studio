"""
GitMem v2.0 — Chunker

Splits large documents or memory strings into smaller chunks for embedding and storage.
Supports simple token-based or semantic splitting.
"""

from typing import List, Dict, Any


class Chunker:
    """Splits large texts into manageable chunks for embedding and storage.

    NOTE on units: `chunk_size` and `chunk_overlap` are measured in **words**
    (whitespace-delimited tokens), not in LLM sub-word tokens.  As a rough
    guide, 1 English word ≈ 1.3 LLM tokens, so:
        chunk_size=500 words  ≈  650 tokens
        chunk_size=350 words  ≈  455 tokens  (good for a ~512-token budget)
    Adjust accordingly when integrating with the TokenPacker, which measures
    context in LLM tokens (tiktoken).
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Args:
            chunk_size:    Maximum number of *words* per chunk (≈ 1.3× tokens).
            chunk_overlap: Number of *words* from the end of one chunk to
                           include at the start of the next, for context
                           continuity across chunk boundaries.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Splits text into chunks of roughly `chunk_size` tokens/words, 
        with `chunk_overlap` overlap.
        (v2.0 uses simple word/char splitting; ideally integrate tiktoken)
        """
        if not text:
            return []
            
        # Very naive implementation for v2.0 MVP - split by words
        words = text.split()
        chunks = []
        
        if len(words) <= self.chunk_size:
            chunks.append({
                "text": text,
                "metadata": metadata or {},
                "chunk_index": 0
            })
            return chunks
            
        i = 0
        chunk_idx = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunk_meta = dict(metadata or {})
            chunk_meta["chunk_index"] = chunk_idx
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_meta
            })
            
            i += (self.chunk_size - self.chunk_overlap)
            chunk_idx += 1
            
        return chunks
