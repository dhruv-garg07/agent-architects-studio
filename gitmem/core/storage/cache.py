"""
GitMem v2.0 — Hot Object Cache

In-memory LRU cache for frequently accessed Merkle DAG objects.
Redis-ready interface: when scaling requires it, swap implementation.
For v2.0: in-process OrderedDict.
"""

from collections import OrderedDict
from typing import Optional, Dict, Any
import threading


class ObjectCache:
    """
    LRU cache for hot Supabase Storage objects.
    
    Thread-safe. Prevents repeated downloads of the same
    SHA-addressed blobs from Supabase Storage Buckets.
    
    Interface is Redis-compatible for future swap:
        get(key) -> value | None
        set(key, value)
        invalidate(key)
        clear()
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, sha: str) -> Optional[Dict[str, Any]]:
        """Get an object by SHA. Returns None on miss."""
        with self._lock:
            if sha in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(sha)
                self._hits += 1
                return self._cache[sha]
            self._misses += 1
            return None

    def set(self, sha: str, data: Dict[str, Any]) -> None:
        """Cache an object by SHA."""
        with self._lock:
            if sha in self._cache:
                self._cache.move_to_end(sha)
                self._cache[sha] = data
            else:
                if len(self._cache) >= self._max_size:
                    # Evict least recently used
                    self._cache.popitem(last=False)
                self._cache[sha] = data

    def invalidate(self, sha: str) -> None:
        """Remove a specific entry."""
        with self._lock:
            self._cache.pop(sha, None)

    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "0%"
            }
