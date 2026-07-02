"""
Memory Classifier — Heuristic-based classification and importance scoring.

Classifies memory entries by:
1. Cognitive type (memory_type): episodic, semantic, procedural, working, state
2. Storage bin (storage_bin): context, vector, document
3. Importance score: 0.0 – 1.0

All classification is done via pure Python heuristics — zero LLM calls.
The LLM may provide a suggested classification, which is used as a hint
but can be overridden by strong heuristic signals.
"""

import re
from typing import Dict, Optional, Tuple
from SimpleMem.models.memory_entry import MemoryEntry


# ── Cognitive Type Patterns ──────────────────────────────────────────────────

# Procedural: instructions, code, how-to
_PROCEDURAL_PATTERNS = [
    r'\bhow\s+to\b', r'\bstep[s]?\s*\d', r'\bdef\s+\w+\s*\(',
    r'\bfunction\s+\w+', r'\bclass\s+\w+', r'\bimport\s+\w+',
    r'\breturn\s+', r'\bfor\s+\w+\s+in\b', r'\bwhile\s+',
    r'\btry\s*:', r'\bexcept\s+', r'\binstall\b.*\bpip\b',
    r'\brun\b.*\bcommand\b', r'\bexecute\b', r'\bprocedure\b',
    r'\bworkflow\b', r'\balgorithm\b', r'\brecipe\b',
    r'\binstructions?\b', r'\btutorial\b', r'\bguide\b',
    r'```',  # Code blocks
]

# Semantic: definitional facts, knowledge
_SEMANTIC_PATTERNS = [
    r'\bis\s+a\b', r'\bis\s+an\b', r'\bis\s+the\b',
    r'\bare\s+defined\s+as\b', r'\bmeans?\b.*\bthat\b',
    r'\bfact\s*:', r'\bdefinition\s*:', r'\bconcept\b',
    r'\btheory\b', r'\bprinciple\b', r'\blaw\s+of\b',
    r'\bformula\b', r'\bequation\b', r'\bconstant\b',
    r'\bspecification\b', r'\bstandard\b', r'\bprotocol\b',
    r'\bcategoriz', r'\bclassif', r'\btaxonomy\b',
    r'\bknown\s+as\b', r'\brefers?\s+to\b',
]

# Working: transient, in-progress
_WORKING_PATTERNS = [
    r'\bcurrently\b', r'\bright\s+now\b', r'\bat\s+the\s+moment\b',
    r'\bin\s+progress\b', r'\bongoing\b', r'\bpending\b',
    r'\bwill\s+do\b', r'\bplanning\s+to\b', r'\babout\s+to\b',
    r'\btemporar(ily|y)\b', r'\bfor\s+now\b', r'\buntil\b',
    r'\bwaiting\s+for\b', r'\bblocked\s+on\b',
]

# State: configuration, preferences, system state
_STATE_PATTERNS = [
    r'\bprefer(s|ence|red)?\b', r'\bsetting[s]?\b',
    r'\bconfig(uration|ured)?\b', r'\bdefault\b',
    r'\benabled?\b', r'\bdisabled?\b', r'\bmode\b',
    r'\btheme\b', r'\blanguage\s+preference\b',
    r'\bnotification\b', r'\bpermission\b',
    r'\brole\b.*\b(admin|user|member)\b',
    r'\bprofile\b', r'\baccount\b',
]

# Episodic indicators: time-anchored events, personal experiences
_EPISODIC_PATTERNS = [
    r'\bdiscussed\b', r'\bmet\s+with\b', r'\bwent\s+to\b',
    r'\battended\b', r'\bvisited\b', r'\btraveled\b',
    r'\bhappened\b', r'\boccurred\b', r'\btook\s+place\b',
    r'\byesterday\b', r'\blast\s+(week|month|year)\b',
    r'\bon\s+\d{4}-\d{2}-\d{2}\b', r'\bat\s+\d{1,2}:\d{2}\b',
    r'\bmeeting\b', r'\bcall\b', r'\bevent\b',
    r'\bexperience[d]?\b', r'\bremember\b',
]


def _count_pattern_matches(text: str, patterns: list) -> int:
    """Count how many patterns match in the text."""
    text_lower = text.lower()
    count = 0
    for pattern in patterns:
        if re.search(pattern, text_lower):
            count += 1
    return count


class MemoryClassifier:
    """
    Heuristic memory classifier and importance scorer.
    
    Runs post-LLM-parse on MemoryEntry objects. Uses keyword/pattern
    analysis to classify cognitive type and storage bin, and computes
    importance from content signals.
    
    The LLM may provide a suggested classification via llm_suggestion dict.
    Strong heuristic signals override the LLM suggestion; weak signals
    defer to it.
    """

    # Minimum pattern matches needed to override an LLM suggestion
    OVERRIDE_THRESHOLD = 2

    def classify_and_score(
        self,
        entry: MemoryEntry,
        llm_suggestion: Optional[Dict[str, str]] = None
    ) -> MemoryEntry:
        """
        Classify and score a MemoryEntry in-place.
        
        Args:
            entry: The MemoryEntry to classify
            llm_suggestion: Optional dict with keys 'memory_type' and 'storage_bin'
                           from the LLM's JSON response
        
        Returns:
            The same MemoryEntry with updated memory_type, storage_bin, importance
        """
        llm_suggestion = llm_suggestion or {}

        # 1. Classify cognitive type
        entry.memory_type = self._classify_cognitive_type(
            entry, llm_suggestion.get("memory_type")
        )

        # 2. Classify storage bin
        entry.storage_bin = self._classify_storage_bin(
            entry, llm_suggestion.get("storage_bin")
        )

        # 3. Score importance
        entry.importance = self._score_importance(entry)

        return entry

    def _classify_cognitive_type(
        self,
        entry: MemoryEntry,
        llm_hint: Optional[str] = None
    ) -> str:
        """
        Determine the cognitive memory type using pattern matching.
        
        Priority order (when pattern matches are strong):
        procedural > semantic > state > working > episodic (default)
        
        If pattern signal is weak (< OVERRIDE_THRESHOLD), defer to LLM hint.
        """
        text = entry.lossless_restatement

        scores = {
            "procedural": _count_pattern_matches(text, _PROCEDURAL_PATTERNS),
            "semantic":   _count_pattern_matches(text, _SEMANTIC_PATTERNS),
            "working":    _count_pattern_matches(text, _WORKING_PATTERNS),
            "state":      _count_pattern_matches(text, _STATE_PATTERNS),
            "episodic":   _count_pattern_matches(text, _EPISODIC_PATTERNS),
        }

        # Boost episodic if entry has temporal anchoring or person references
        if entry.timestamp:
            scores["episodic"] += 1
        if entry.persons and len(entry.persons) > 0:
            scores["episodic"] += 1

        # Find the best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        # If strong signal, use heuristic result
        if best_score >= self.OVERRIDE_THRESHOLD:
            return best_type

        # If weak signal, prefer LLM hint if valid
        valid_types = {"episodic", "semantic", "procedural", "working", "state"}
        if llm_hint and llm_hint.lower() in valid_types:
            return llm_hint.lower()

        # Fallback: if any pattern matched, use it; otherwise default to episodic
        if best_score > 0:
            return best_type
        return "episodic"

    def _classify_storage_bin(
        self,
        entry: MemoryEntry,
        llm_hint: Optional[str] = None
    ) -> str:
        """
        Determine the storage bin based on content shape.
        
        - context: Short structured facts (< 300 chars, has entities/persons/topic)
        - document: Long-form reference (> 500 chars, or code blocks, or multi-paragraph)
        - vector: Everything else (optimized for embedding similarity)
        """
        text = entry.lossless_restatement
        text_len = len(text)

        # Strong signals for 'document'
        has_code_blocks = "```" in text
        is_long_form = text_len > 500
        is_multi_paragraph = text.count("\n\n") >= 2

        if has_code_blocks or is_long_form or is_multi_paragraph:
            return "document"

        # Strong signals for 'context'
        has_structured_metadata = bool(entry.topic) and (
            bool(entry.persons) or bool(entry.entities)
        )
        is_short = text_len < 300

        if is_short and has_structured_metadata:
            return "context"

        # Medium-length with rich metadata → still context
        if text_len < 400 and has_structured_metadata and entry.timestamp:
            return "context"

        # Check LLM hint
        valid_bins = {"context", "vector", "document"}
        if llm_hint and llm_hint.lower() in valid_bins:
            return llm_hint.lower()

        # Default: vector (optimized for similarity search)
        return "vector"

    def _score_importance(self, entry: MemoryEntry) -> float:
        """
        Compute importance score (0.0 – 1.0) from content signals.
        
        Weighted signal breakdown:
        - Entity count:        0.15  (more entities → more important, capped at 5)
        - Person count:        0.15  (named persons → higher relevance)
        - Temporal anchoring:  0.10  (has timestamp → more verifiable)
        - Keyword count:       0.10  (more keywords → richer information)
        - Content length:      0.10  (longer → more substance, capped at 500)
        - Topic specificity:   0.10  (has topic → more organized)
        - Location presence:   0.05  (has location → more grounded)
        - Procedural bonus:    0.10  (procedural knowledge is high-value)
        - Semantic bonus:      0.10  (definitional facts are stable)
        - Base score:          0.05  (minimum baseline)
        """
        score = 0.05  # Base score

        # Entity count (0 – 0.15)
        entity_count = len(entry.entities) if entry.entities else 0
        score += min(entity_count / 5.0, 1.0) * 0.15

        # Person count (0 – 0.15)
        person_count = len(entry.persons) if entry.persons else 0
        score += min(person_count / 3.0, 1.0) * 0.15

        # Temporal anchoring (0 or 0.10)
        if entry.timestamp:
            score += 0.10

        # Keyword count (0 – 0.10)
        keyword_count = len(entry.keywords) if entry.keywords else 0
        score += min(keyword_count / 5.0, 1.0) * 0.10

        # Content length (0 – 0.10)
        content_len = len(entry.lossless_restatement)
        score += min(content_len / 500.0, 1.0) * 0.10

        # Topic specificity (0 or 0.10)
        if entry.topic:
            score += 0.10

        # Location presence (0 or 0.05)
        if entry.location:
            score += 0.05

        # Cognitive type bonuses (0 or 0.10)
        if entry.memory_type == "procedural":
            score += 0.10
        elif entry.memory_type == "semantic":
            score += 0.10
        elif entry.memory_type == "state":
            score += 0.05  # State is moderately important

        # Clamp to [0.0, 1.0]
        return round(min(max(score, 0.0), 1.0), 3)
