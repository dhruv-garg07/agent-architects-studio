"""
Cross-Encoder Reranker Utility.
Uses FlashRank for ultra-lightweight, ONNX-based reranking.
"""
import logging
from typing import List, Dict, Any

try:
    from flashrank import Ranker, RerankRequest
    FLASHRANK_AVAILABLE = True
except Exception as e:
    FLASHRANK_AVAILABLE = False
    logging.warning(f"flashrank not available, reranking will be a no-op: {e}")

logger = logging.getLogger(__name__)

class Reranker:
    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2"):
        self.model_name = model_name
        self.model = None
        if FLASHRANK_AVAILABLE:
            try:
                # Flashrank automatically downloads ultra-lightweight ONNX models (~14MB)
                self.model = Ranker(model_name=self.model_name)
            except Exception as e:
                logger.error(f"Failed to load FlashRank model: {e}")
                self.model = None

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks a list of documents based on the query.
        Each document should be a dict with a 'text' key.
        """
        if not documents:
            return []
            
        if not self.model:
            logger.warning("Reranker model not loaded. Returning original documents.")
            return documents[:top_k]
            
        try:
            # FlashRank expects passages as a list of dicts containing "id" and "text"
            passages = []
            for idx, doc in enumerate(documents):
                passages.append({
                    "id": str(idx),
                    "text": doc.get('text', ''),
                    "meta": doc.get('metadata', {})
                })
                
            rerankrequest = RerankRequest(query=query, passages=passages)
            results = self.model.rerank(rerankrequest)
            
            # Reconstruct the original format but sorted and truncated
            ranked_docs = []
            for res in results[:top_k]:
                ranked_docs.append({
                    "text": res["text"],
                    "metadata": res.get("meta", {})
                })
            
            return ranked_docs
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return documents[:top_k]
