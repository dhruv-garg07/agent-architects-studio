"""
GitMem v2.0 — Object Store

Cloud-native content-addressable storage for AI Memory.
Implements the Git-like Merkle DAG (Blobs, Trees, Commits) on top of
Supabase Storage Buckets, replacing the local filesystem implementation.

Objects are stored in the 'gitmem-objects' bucket as zlib-compressed JSON blobs:
    objects/{sha}.json.zlib
"""

import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import zlib


class ObjectType(str, Enum):
    BLOB = "blob"       # Raw memory content
    TREE = "tree"       # Directory/collection of memories
    COMMIT = "commit"   # Snapshot with parent links


@dataclass
class MemoryBlob:
    """Raw memory content, content-addressed by SHA-256."""
    content: str
    memory_type: str = "episodic"
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def sha(self) -> str:
        """Compute SHA-256 hash of the blob content."""
        raw = json.dumps(self.to_dict(), sort_keys=True).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "type": ObjectType.BLOB.value,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryBlob':
        return cls(
            content=data["content"],
            memory_type=data.get("memory_type", "episodic"),
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


@dataclass
class TreeEntry:
    """An entry in a cognitive tree - references a blob."""
    mode: str           # "memory", "fact", "procedure", "state"
    sha: str            # SHA of the blob
    path: str           # Logical path (e.g., "episodic/observation-001")
    name: str           # Human-readable name
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode,
            "sha": self.sha,
            "path": self.path,
            "name": self.name
        }


@dataclass
class CognitiveTree:
    """A snapshot of cognitive state - collection of memory references."""
    entries: List[TreeEntry] = field(default_factory=list)
    
    @property
    def sha(self) -> str:
        """Compute SHA-256 hash of the tree."""
        raw = json.dumps(self.to_dict(), sort_keys=True).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "type": ObjectType.TREE.value,
            "entries": [e.to_dict() for e in self.entries]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CognitiveTree':
        entries = [TreeEntry(**e) for e in data.get("entries", [])]
        return cls(entries=entries)
    
    def add_entry(self, entry: TreeEntry):
        self.entries.append(entry)
    
    def get_entry(self, path: str) -> Optional[TreeEntry]:
        for e in self.entries:
            if e.path == path:
                return e
        return None


@dataclass
class MemoryCommit:
    """Immutable commit object - snapshot of cognitive state."""
    tree_sha: str                           # SHA of root tree
    message: str
    author: str
    agent_id: str
    parents: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    stats: Dict[str, int] = field(default_factory=dict)
    
    @property
    def sha(self) -> str:
        """Compute SHA-256 hash of the commit."""
        raw = json.dumps(self.to_dict(), sort_keys=True).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()
    
    def to_dict(self) -> Dict:
        return {
            "type": ObjectType.COMMIT.value,
            "tree": self.tree_sha,
            "parents": self.parents,
            "author": self.author,
            "agent_id": self.agent_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "stats": self.stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryCommit':
        return cls(
            tree_sha=data["tree"],
            message=data["message"],
            author=data.get("author", "system"),
            agent_id=data.get("agent_id", "system"),
            parents=data.get("parents", []),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            stats=data.get("stats", {})
        )


class ObjectStore:
    """
    Cloud-native content-addressable object storage for GitMem using Supabase Storage.
    Objects are compressed with zlib and stored by their SHA-256 hash.
    
    Features hot object caching to minimize downloads.
    """
    
    def __init__(self, supabase_client, bucket_name: str = "gitmem-objects", cache=None):
        self.client = supabase_client
        self.bucket = bucket_name
        self.cache = cache  # core.cache.ObjectCache instance
        
        if self.client:
            try:
                # Try to get the bucket. If it fails, try to create it.
                self.client.storage.get_bucket(self.bucket)
            except Exception:
                try:
                    self.client.storage.create_bucket(self.bucket, options={'public': False})
                    print(f"[ObjectStore] Created missing storage bucket: {self.bucket}")
                except Exception as e:
                    print(f"[ObjectStore] Warning: Could not ensure bucket '{self.bucket}' exists: {e}")
            
            self.storage = self.client.storage.from_(self.bucket)
        else:
            self.storage = None

    def _blob_path(self, sha: str) -> str:
        return f"objects/{sha}.json.zlib"
    
    # ========== Core Storage Operations ==========
    
    def write_object(self, obj_data: Dict, sha: str) -> str:
        """Write an object to Supabase Storage."""
        if self.cache:
            self.cache.set(sha, obj_data)
            
        if not self.storage:
            return sha
            
        try:
            # Check if exists first
            if self.object_exists(sha):
                return sha
                
            compressed = zlib.compress(json.dumps(obj_data, sort_keys=True).encode('utf-8'))
            path = self._blob_path(sha)
            self.storage.upload(path, compressed, file_options={"content-type": "application/octet-stream"})
        except Exception as e:
            # If already exists, storage.upload throws an error, which we can ignore safely
            if "Duplicate" not in str(e):
                print(f"[ObjectStore] Upload failed for {sha}: {e}")
        
        return sha
    
    def read_object(self, sha: str) -> Optional[Dict]:
        """Read an object from Supabase Storage (with caching)."""
        # Skip invalid SHAs (non-hex or too short)
        if not sha or len(sha) < 8 or sha in ("init", "HEAD", "undefined"):
            return None
            
        if self.cache:
            cached = self.cache.get(sha)
            if cached is not None:
                return cached
                
        if not self.storage:
            return None
            
        try:
            path = self._blob_path(sha)
            data = self.storage.download(path)
            raw = zlib.decompress(data)
            obj_data = json.loads(raw.decode('utf-8'))
            
            if self.cache:
                self.cache.set(sha, obj_data)
                
            return obj_data
        except Exception as e:
            if "Bucket not found" in str(e):
                print(f"[ObjectStore] Critical: Bucket '{self.bucket}' not found in Supabase Storage.")
            elif "not found" in str(e).lower() or "not_found" in str(e).lower() or "404" in str(e):
                pass  # Object doesn't exist, this is expected in some Git operations
            else:
                print(f"[ObjectStore] Read failed for {sha}: {e}")
            return None
    
    def object_exists(self, sha: str) -> bool:
        """Check if an object exists in Supabase Storage."""
        if not sha or len(sha) < 8 or sha in ("init", "HEAD", "undefined"):
            return False
            
        if self.cache and self.cache.get(sha) is not None:
            return True
            
        if not self.storage:
            return False
            
        try:
            path = self._blob_path(sha)
            # Check if bucket exists first by a small operation or assume it exists
            # but handle error in list
            files = self.storage.list("objects")
            for f in files:
                if f.get("name") == f"{sha}.json.zlib":
                    return True
            return False
        except Exception as e:
            if "Bucket not found" in str(e):
                 print(f"[ObjectStore] Critical: Bucket '{self.bucket}' missing.")
            return False
    
    # ========== High-Level Operations ==========
    
    def store_blob(self, blob: MemoryBlob) -> str:
        """Store a memory blob and return its SHA."""
        sha = blob.sha
        if not self.object_exists(sha):
            self.write_object(blob.to_dict(), sha)
        return sha
    
    def store_tree(self, tree: CognitiveTree) -> str:
        """Store a cognitive tree and return its SHA."""
        sha = tree.sha
        if not self.object_exists(sha):
            self.write_object(tree.to_dict(), sha)
        return sha
        
    def store_commit(self, commit: MemoryCommit) -> str:
        """Store a commit and return its SHA."""
        sha = commit.sha
        if not self.object_exists(sha):
            self.write_object(commit.to_dict(), sha)
        return sha
        
    def get_blob(self, sha: str) -> Optional[MemoryBlob]:
        """Retrieve a blob by SHA."""
        data = self.read_object(sha)
        if data and data.get("type") == ObjectType.BLOB.value:
            return MemoryBlob.from_dict(data)
        return None
        
    def get_tree(self, sha: str) -> Optional[CognitiveTree]:
        """Retrieve a tree by SHA."""
        data = self.read_object(sha)
        if data and data.get("type") == ObjectType.TREE.value:
            return CognitiveTree.from_dict(data)
        return None
        
    def get_commit(self, sha: str) -> Optional[MemoryCommit]:
        """Retrieve a commit by SHA."""
        data = self.read_object(sha)
        if data and data.get("type") == ObjectType.COMMIT.value:
            return MemoryCommit.from_dict(data)
        return None
