"""
GitMem v2.0 — Memory Classifier

Automatically classifies memory type (episodic, semantic, procedural) 
and assigns an importance score based on the content.
"""

from typing import Dict, Any, Tuple, List
from gitmem.core.models import MemoryType


class Classifier:
    """Classifies raw inputs into structured memory properties."""

    def __init__(self):
        pass

    def classify(self, text: str, metadata: Dict[str, Any] = None) -> Tuple[MemoryType, float, List[str]]:
        """
        Analyze text to determine:
        1. MemoryType
        2. Importance score (0.0 to 1.0)
        3. Extracted tags
        
        Returns: (MemoryType, importance, tags)
        """
        text_lower = text.lower()
        
        # 1. Classify Type
        m_type = MemoryType.EPISODIC
        if "how to" in text_lower or "def " in text_lower or "function" in text_lower:
            m_type = MemoryType.PROCEDURAL
        elif "is a" in text_lower or "fact:" in text_lower:
            m_type = MemoryType.SEMANTIC
            
        # 2. Determine Importance
        importance = 0.5
        if "critical" in text_lower or "error" in text_lower or "important" in text_lower:
            importance = 0.8
        elif len(text) < 20:
            importance = 0.2
            
        # 3. Extract Tags (Stub)
        tags = []
        if metadata and "tags" in metadata:
            tags = metadata["tags"]
            
        return m_type, importance, tags
