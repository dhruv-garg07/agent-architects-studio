"""
Unified Chunking Utility for RAG processing.
"""
from typing import List, Dict, Any
import logging

try:
    from Octave_mem.RAG_DB_CONTROLLER.utlis_docs.doc_control_chunks import AdvancedChunker
    ADVANCED_AVAILABLE = True
except ImportError as e:
    ADVANCED_AVAILABLE = False
    logging.warning(f"Advanced chunker not available: {e}")

logger = logging.getLogger(__name__)

class UnifiedChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, mode: str = "fast"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.mode = mode
        
        if self.mode == "advanced" and ADVANCED_AVAILABLE:
            self.advanced_chunker = AdvancedChunker()
        elif self.mode == "advanced":
            logger.warning("Advanced chunker dependencies not met, falling back to fast mode.")
            self.mode = "fast"

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Splits text into chunks using either fast or advanced mode.
        """
        if not text:
            return []
            
        metadata = metadata or {}
        
        if self.mode == "advanced":
            try:
                advanced_chunks = self.advanced_chunker.process_document(text)
                result = []
                for idx, c in enumerate(advanced_chunks):
                    meta = dict(metadata)
                    meta.update({
                        "chunk_index": idx,
                        "title": c.get('title', ''),
                        "tokens": c.get('tokens', 0)
                    })
                    result.append({
                        "text": c.get('text', ''),
                        "metadata": meta
                    })
                return result
            except Exception as e:
                logger.error(f"Advanced chunking failed, falling back to fast mode: {e}")
                
        # Fast mode fallback (word-based)
        words = text.split()
        chunks = []
        
        if len(words) <= self.chunk_size:
            meta = dict(metadata)
            meta["chunk_index"] = 0
            chunks.append({
                "text": text,
                "metadata": meta
            })
            return chunks
            
        i = 0
        chunk_idx = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunk_meta = dict(metadata)
            chunk_meta["chunk_index"] = chunk_idx
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_meta
            })
            
            # ensure progress even if overlap is large
            step = max(1, self.chunk_size - self.chunk_overlap)
            i += step
            chunk_idx += 1
            
        return chunks
