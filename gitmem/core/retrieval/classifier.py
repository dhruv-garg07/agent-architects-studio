"""
GitMem v2.0 — Memory Classifier

Automatically classifies memory type (episodic, semantic, procedural, working, state)
and assigns an importance score based on the content.

Delegates to SimpleMem's MemoryClassifier for heuristic analysis, ensuring
consistent classification logic across both the GitMem ingestion pipeline
and the SimpleMem MemoryBuilder pipeline.
"""

from typing import Dict, Any, Tuple, List
from gitmem.core.models import MemoryType

import sys
import os

# Ensure SimpleMem is importable
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from SimpleMem.core.memory_classifier import MemoryClassifier as HeuristicClassifier
from SimpleMem.models.memory_entry import MemoryEntry


# Map string type names to MemoryType enum values
_TYPE_MAP = {
    "episodic": MemoryType.EPISODIC,
    "semantic": MemoryType.SEMANTIC,
    "procedural": MemoryType.PROCEDURAL,
    "state": MemoryType.STATE,
    "working": MemoryType.EPISODIC,  # Working maps to episodic in the GitMem enum (no WORKING variant)
}


class Classifier:
    """Classifies raw inputs into structured memory properties.
    
    Uses the shared heuristic MemoryClassifier from SimpleMem for consistent
    classification across both pipelines (GitMem ingestion + SimpleMem builder).
    """

    def __init__(self):
        self._heuristic = HeuristicClassifier()

    def classify(self, text: str, metadata: Dict[str, Any] = None) -> Tuple[MemoryType, float, List[str]]:
        """
        Analyze text to determine:
        1. MemoryType
        2. Importance score (0.0 to 1.0)
        3. Extracted tags
        
        Returns: (MemoryType, importance, tags)
        """
        # Build a temporary MemoryEntry for the heuristic classifier
        entry = MemoryEntry(
            lossless_restatement=text,
            keywords=metadata.get("keywords", []) if metadata else [],
            timestamp=metadata.get("timestamp") if metadata else None,
            location=metadata.get("location") if metadata else None,
            persons=metadata.get("persons", []) if metadata else [],
            entities=metadata.get("entities", []) if metadata else [],
            topic=metadata.get("topic") if metadata else None,
        )

        # Run heuristic classification
        entry = self._heuristic.classify_and_score(entry)

        # Map to GitMem MemoryType enum
        m_type = _TYPE_MAP.get(entry.memory_type, MemoryType.EPISODIC)
        importance = entry.importance

        # Extract tags
        tags = []
        if metadata and "tags" in metadata:
            tags = metadata["tags"]

        return m_type, importance, tags
