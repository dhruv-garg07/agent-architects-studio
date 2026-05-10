"""
GitMem v2.0 — Relevance Ranker

Multi-signal scoring to rank retrieved memory candidates.
Combines semantic similarity, recency decay, and intrinsic importance.
"""

from typing import List, Dict, Any
from datetime import datetime
import math


class Ranker:
    """Reranks memory candidates based on multiple signals."""
    
    def __init__(self, w_semantic: float = 1.0, w_recency: float = 0.5, 
                 w_importance: float = 0.8, w_frequency: float = 0.2):
        self.w_semantic = w_semantic
        self.w_recency = w_recency
        self.w_importance = w_importance
        self.w_frequency = w_frequency

    def rerank(self, candidates: List[Dict[str, Any]], query_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Rank a list of memory dictionaries.
        Expected keys in candidate dict:
        - "content": str
        - "semantic_score": float (0.0 to 1.0, from vector DB)
        - "importance": float (0.0 to 1.0)
        - "created_at": str (ISO format)
        - "access_count": int (optional)
        """
        if not candidates:
            return []
            
        now = query_time or datetime.now()
        
        for cand in candidates:
            # Semantic (default to 0.5 if not from vector search)
            s_score = cand.get("semantic_score", 0.5)
            
            # Importance
            i_score = cand.get("importance", 0.5)
            
            # Recency Decay
            try:
                created_at = datetime.fromisoformat(cand.get("created_at", now.isoformat()).replace('Z', '+00:00'))
                # Replace tzinfo for naive subtraction if necessary, or just use timestamp
                delta_hours = abs((now.timestamp() - created_at.timestamp()) / 3600)
                # Simple exponential decay: half-life of ~48 hours
                r_score = math.exp(-0.014 * delta_hours)
            except Exception:
                r_score = 0.5
                
            # Access Frequency
            f_score = min(cand.get("access_count", 0) / 10.0, 1.0)
            
            # Final Multi-Signal Score
            final_score = (
                (self.w_semantic * s_score) +
                (self.w_recency * r_score) +
                (self.w_importance * i_score) +
                (self.w_frequency * f_score)
            )
            
            cand["_rank_score"] = final_score
            
        # Sort descending
        ranked = sorted(candidates, key=lambda x: x.get("_rank_score", 0), reverse=True)
        return ranked
