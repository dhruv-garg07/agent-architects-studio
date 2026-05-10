"""
GitMem v2.0 — Merge Engine

Handles merging of cognitive states and resolving conflicts.
Supports different semantic merge policies:
- LAST_WRITE_WINS: The newer object overwrites the older.
- IMPORTANCE_PRIORITY: The object with higher importance wins.
- SEMANTIC_MERGE: (Stub) AI intelligently merges the content.
- MANUAL_CONFLICT: Leaves conflict markers or fails.
"""

from typing import Dict, Any, List, Optional
from gitmem.core.models import MergePolicy
from gitmem.core.vcs.object_store import ObjectStore, CognitiveTree, TreeEntry
from gitmem.core.vcs.diff_engine import DiffEngine
import copy


class MergeConflict(Exception):
    pass


class MergeEngine:
    """Merges cognitive states and branches."""
    
    def __init__(self, object_store: ObjectStore, diff_engine: DiffEngine):
        self.store = object_store
        self.diff_engine = diff_engine

    def merge_trees(self, base_sha: str, target_sha: str, source_sha: str, 
                    policy: MergePolicy = MergePolicy.LAST_WRITE_WINS) -> str:
        """
        3-way merge of trees.
        Returns the SHA of the new merged tree.
        """
        base_tree = self.store.get_tree(base_sha) if base_sha else CognitiveTree()
        target_tree = self.store.get_tree(target_sha) if target_sha else CognitiveTree()
        source_tree = self.store.get_tree(source_sha) if source_sha else CognitiveTree()
        
        # Maps for quick lookup
        base_entries = {e.path: e for e in base_tree.entries}
        target_entries = {e.path: e for e in target_tree.entries}
        source_entries = {e.path: e for e in source_tree.entries}
        
        # The new tree we are building
        merged_entries: Dict[str, TreeEntry] = {}
        
        # Get all unique paths across all trees
        all_paths = set(base_entries.keys()) | set(target_entries.keys()) | set(source_entries.keys())
        
        for path in all_paths:
            base = base_entries.get(path)
            target = target_entries.get(path)
            source = source_entries.get(path)
            
            # 1. Path deleted in both branches -> deleted in merge
            if not target and not source:
                continue
                
            # 2. Path added/modified in target, not in source -> keep target
            if not base and target and not source:
                merged_entries[path] = target
                continue
            if base and target and not source and target.sha != base.sha:
                merged_entries[path] = target
                continue
                
            # 3. Path added/modified in source, not in target -> keep source
            if not base and not target and source:
                merged_entries[path] = source
                continue
            if base and not target and source and source.sha != base.sha:
                merged_entries[path] = source
                continue
                
            # 4. Path unchanged in both branches -> keep base (or target/source)
            if base and target and source and target.sha == base.sha and source.sha == base.sha:
                merged_entries[path] = base
                continue
                
            # 5. Path changed only in target -> keep target
            if base and target and source and target.sha != base.sha and source.sha == base.sha:
                merged_entries[path] = target
                continue
                
            # 6. Path changed only in source -> keep source
            if base and target and source and target.sha == base.sha and source.sha != base.sha:
                merged_entries[path] = source
                continue
                
            # 7. Path changed in BOTH to SAME thing -> keep either
            if target and source and target.sha == source.sha:
                merged_entries[path] = target
                continue
                
            # 8. CONFLICT: Changed in both to different things, or added in both differently
            merged_entry = self._resolve_conflict(path, target, source, policy)
            if merged_entry:
                merged_entries[path] = merged_entry
                
        # Create and store new tree
        new_tree = CognitiveTree(entries=list(merged_entries.values()))
        return self.store.store_tree(new_tree)
        
    def _resolve_conflict(self, path: str, target: Optional[TreeEntry], source: Optional[TreeEntry], 
                          policy: MergePolicy) -> Optional[TreeEntry]:
        """Resolve a conflict between two tree entries based on the policy."""
        if policy == MergePolicy.MANUAL_CONFLICT:
            raise MergeConflict(f"Manual conflict resolution required for path: {path}")
            
        if not target: return source
        if not source: return target
        
        # Retrieve blobs to apply policies based on metadata (timestamps, importance)
        target_blob = self.store.get_blob(target.sha)
        source_blob = self.store.get_blob(source.sha)
        
        if policy == MergePolicy.IMPORTANCE_PRIORITY:
            # Fallback to source if blobs can't be fetched or importance is equal
            if target_blob and source_blob:
                if target_blob.importance > source_blob.importance:
                    return target
                elif source_blob.importance > target_blob.importance:
                    return source
                    
        # LAST_WRITE_WINS or fallback for IMPORTANCE_PRIORITY
        if target_blob and source_blob:
            target_time = target_blob.created_at
            source_time = source_blob.created_at
            if target_time > source_time:
                return target
                
        # SEMANTIC_MERGE would invoke an LLM here. For now, default to source (the incoming change).
        return source

    def cherry_pick(self, commit_sha: str, current_tree_sha: str, 
                    policy: MergePolicy = MergePolicy.LAST_WRITE_WINS) -> str:
        """
        Cherry-pick a commit onto the current tree.
        Effectively a merge where base is the commit's parent, target is current tree, source is the commit.
        """
        commit = self.store.get_commit(commit_sha)
        if not commit:
            raise ValueError(f"Commit not found: {commit_sha}")
            
        parent_sha = commit.parents[0] if commit.parents else None
        parent_commit = self.store.get_commit(parent_sha) if parent_sha else None
        base_tree_sha = parent_commit.tree_sha if parent_commit else None
        
        return self.merge_trees(base_tree_sha, current_tree_sha, commit.tree_sha, policy)
