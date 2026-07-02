"""
Unit tests for MemoryClassifier — heuristic classification and importance scoring.

Tests:
1. Cognitive type classification (episodic, semantic, procedural, working, state)
2. Storage bin classification (context, vector, document)
3. Importance scoring (range 0.0 – 1.0, signal-based)
4. LLM hint integration (used when heuristic signal is weak)
"""

import sys
import os

# Ensure all packages are importable:
# project_root = agent-architects-studio (for gitmem, Octave_mem)
# lib_dir = agent-architects-studio/lib (for SimpleMem)
tests_dir = os.path.dirname(os.path.abspath(__file__))       # lib/SimpleMem/tests
simplemem_dir = os.path.dirname(tests_dir)                    # lib/SimpleMem
lib_dir = os.path.dirname(simplemem_dir)                      # lib
project_root = os.path.dirname(lib_dir)                       # agent-architects-studio

for p in [project_root, lib_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from SimpleMem.core.memory_classifier import MemoryClassifier
from SimpleMem.models.memory_entry import MemoryEntry


def make_entry(**kwargs):
    """Helper to create a MemoryEntry with defaults."""
    defaults = {
        "lossless_restatement": "Test memory content.",
        "keywords": [],
        "timestamp": None,
        "location": None,
        "persons": [],
        "entities": [],
        "topic": None,
    }
    defaults.update(kwargs)
    return MemoryEntry(**defaults)


classifier = MemoryClassifier()


# ═══════════════════════════════════════════════════════════════════
# Test 1: Cognitive Type Classification
# ═══════════════════════════════════════════════════════════════════

def test_procedural_classification():
    """Code/instruction content should be classified as procedural."""
    entry = make_entry(
        lossless_restatement="How to install Python: Step 1, download the installer. Step 2, run the installer.",
        keywords=["Python", "install", "tutorial"]
    )
    result = classifier.classify_and_score(entry)
    assert result.memory_type == "procedural", f"Expected 'procedural', got '{result.memory_type}'"
    print("✓ test_procedural_classification passed")


def test_procedural_code_block():
    """Content with code blocks should be classified as procedural."""
    entry = make_entry(
        lossless_restatement="```python\ndef hello():\n    print('Hello')\n```"
    )
    result = classifier.classify_and_score(entry)
    assert result.memory_type == "procedural", f"Expected 'procedural', got '{result.memory_type}'"
    print("✓ test_procedural_code_block passed")


def test_semantic_classification():
    """Definitional facts should be classified as semantic."""
    entry = make_entry(
        lossless_restatement="Python is a high-level programming language. It is known as an interpreted language.",
        keywords=["Python", "programming", "language"]
    )
    result = classifier.classify_and_score(entry)
    assert result.memory_type == "semantic", f"Expected 'semantic', got '{result.memory_type}'"
    print("✓ test_semantic_classification passed")


def test_episodic_classification():
    """Time-anchored events with persons should be classified as episodic."""
    entry = make_entry(
        lossless_restatement="Alice discussed the marketing strategy with Bob at the office on 2025-11-15.",
        keywords=["Alice", "Bob", "marketing"],
        timestamp="2025-11-15T14:30:00",
        persons=["Alice", "Bob"],
        location="office"
    )
    result = classifier.classify_and_score(entry)
    assert result.memory_type == "episodic", f"Expected 'episodic', got '{result.memory_type}'"
    print("✓ test_episodic_classification passed")


def test_working_classification():
    """Transient state content should be classified as working."""
    entry = make_entry(
        lossless_restatement="Currently waiting for the deployment to complete. The build is in progress right now.",
        keywords=["deployment", "build", "in progress"]
    )
    result = classifier.classify_and_score(entry)
    assert result.memory_type == "working", f"Expected 'working', got '{result.memory_type}'"
    print("✓ test_working_classification passed")


def test_state_classification():
    """Configuration/preference content should be classified as state."""
    entry = make_entry(
        lossless_restatement="User preference: dark theme is enabled. Notification settings are configured for email only.",
        keywords=["preference", "theme", "notification", "settings"]
    )
    result = classifier.classify_and_score(entry)
    assert result.memory_type == "state", f"Expected 'state', got '{result.memory_type}'"
    print("✓ test_state_classification passed")


def test_llm_hint_used_when_weak_signal():
    """When heuristic signal is weak, LLM hint should be used."""
    entry = make_entry(
        lossless_restatement="The sky is blue.",  # Minimal signal
        keywords=["sky", "blue"]
    )
    result = classifier.classify_and_score(
        entry,
        llm_suggestion={"memory_type": "semantic", "storage_bin": "context"}
    )
    assert result.memory_type == "semantic", f"Expected 'semantic' (LLM hint), got '{result.memory_type}'"
    print("✓ test_llm_hint_used_when_weak_signal passed")


def test_heuristic_overrides_llm_on_strong_signal():
    """When heuristic signal is strong, it should override LLM hint."""
    entry = make_entry(
        lossless_restatement="How to bake a cake: Step 1, preheat the oven. Step 2, mix the ingredients. Follow these instructions carefully.",
        keywords=["bake", "cake", "recipe", "instructions"]
    )
    result = classifier.classify_and_score(
        entry,
        llm_suggestion={"memory_type": "episodic"}  # LLM says episodic, but it's clearly procedural
    )
    assert result.memory_type == "procedural", f"Expected 'procedural' (override), got '{result.memory_type}'"
    print("✓ test_heuristic_overrides_llm_on_strong_signal passed")


# ═══════════════════════════════════════════════════════════════════
# Test 2: Storage Bin Classification
# ═══════════════════════════════════════════════════════════════════

def test_storage_bin_context():
    """Short facts with rich metadata should be 'context'."""
    entry = make_entry(
        lossless_restatement="Alice works at Google as a software engineer.",
        keywords=["Alice", "Google", "software engineer"],
        persons=["Alice"],
        entities=["Google"],
        topic="Employment"
    )
    result = classifier.classify_and_score(entry)
    assert result.storage_bin == "context", f"Expected 'context', got '{result.storage_bin}'"
    print("✓ test_storage_bin_context passed")


def test_storage_bin_document():
    """Long-form content should be 'document'."""
    entry = make_entry(
        lossless_restatement="A" * 600  # 600 characters
    )
    result = classifier.classify_and_score(entry)
    assert result.storage_bin == "document", f"Expected 'document', got '{result.storage_bin}'"
    print("✓ test_storage_bin_document passed")


def test_storage_bin_document_code():
    """Content with code blocks should be 'document'."""
    entry = make_entry(
        lossless_restatement="Here is the code:\n```python\nprint('hello')\n```"
    )
    result = classifier.classify_and_score(entry)
    assert result.storage_bin == "document", f"Expected 'document', got '{result.storage_bin}'"
    print("✓ test_storage_bin_document_code passed")


def test_storage_bin_vector():
    """Medium content without rich metadata should default to 'vector'."""
    entry = make_entry(
        lossless_restatement="This is a moderately long sentence that doesn't have much structured metadata associated with it but is not super long either."
    )
    result = classifier.classify_and_score(entry)
    assert result.storage_bin == "vector", f"Expected 'vector', got '{result.storage_bin}'"
    print("✓ test_storage_bin_vector passed")


# ═══════════════════════════════════════════════════════════════════
# Test 3: Importance Scoring
# ═══════════════════════════════════════════════════════════════════

def test_importance_range():
    """Importance should always be between 0.0 and 1.0."""
    entry = make_entry(lossless_restatement="Test.")
    result = classifier.classify_and_score(entry)
    assert 0.0 <= result.importance <= 1.0, f"Importance {result.importance} out of range"
    print("✓ test_importance_range passed")


def test_rich_entry_high_importance():
    """Entry with many signals should have high importance."""
    entry = make_entry(
        lossless_restatement="Alice and Bob discussed the Q3 marketing strategy for ProductXYZ at Google HQ in Mountain View on 2025-11-15 at 14:30.",
        keywords=["Alice", "Bob", "Q3", "marketing", "ProductXYZ"],
        timestamp="2025-11-15T14:30:00",
        location="Google HQ, Mountain View",
        persons=["Alice", "Bob"],
        entities=["ProductXYZ", "Google"],
        topic="Q3 Marketing Strategy"
    )
    result = classifier.classify_and_score(entry)
    assert result.importance >= 0.5, f"Expected importance >= 0.5, got {result.importance}"
    print(f"✓ test_rich_entry_high_importance passed (importance={result.importance})")


def test_sparse_entry_low_importance():
    """Entry with minimal signals should have low importance."""
    entry = make_entry(
        lossless_restatement="Ok."
    )
    result = classifier.classify_and_score(entry)
    assert result.importance <= 0.3, f"Expected importance <= 0.3, got {result.importance}"
    print(f"✓ test_sparse_entry_low_importance passed (importance={result.importance})")


def test_procedural_importance_bonus():
    """Procedural entries should get an importance bonus."""
    procedural = make_entry(
        lossless_restatement="How to deploy: Step 1, build the Docker image. Step 2, push to registry.",
        keywords=["deploy", "Docker"],
        topic="Deployment"
    )
    generic = make_entry(
        lossless_restatement="The team had a regular standup meeting.",
        keywords=["standup", "meeting"],
        topic="Meeting"
    )
    
    proc_result = classifier.classify_and_score(procedural)
    gen_result = classifier.classify_and_score(generic)
    
    # Procedural should have higher importance due to type bonus
    assert proc_result.importance > gen_result.importance, \
        f"Procedural ({proc_result.importance}) should be > generic ({gen_result.importance})"
    print(f"✓ test_procedural_importance_bonus passed (proc={proc_result.importance}, gen={gen_result.importance})")


# ═══════════════════════════════════════════════════════════════════
# Run all tests
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Running MemoryClassifier Tests")
    print("=" * 60)
    
    tests = [
        test_procedural_classification,
        test_procedural_code_block,
        test_semantic_classification,
        test_episodic_classification,
        test_working_classification,
        test_state_classification,
        test_llm_hint_used_when_weak_signal,
        test_heuristic_overrides_llm_on_strong_signal,
        test_storage_bin_context,
        test_storage_bin_document,
        test_storage_bin_document_code,
        test_storage_bin_vector,
        test_importance_range,
        test_rich_entry_high_importance,
        test_sparse_entry_low_importance,
        test_procedural_importance_bonus,
    ]
    
    passed = 0
    failed = 0
    
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_fn.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_fn.__name__} ERROR: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
