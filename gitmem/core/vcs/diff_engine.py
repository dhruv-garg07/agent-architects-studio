"""
GitMem v2.0 — Diff Engine

Computes structural differences between cognitive states.
Useful for understanding what changed between two commits.
"""

from typing import Dict, Any, List, Set, Tuple
from gitmem.core.vcs.object_store import ObjectStore, CognitiveTree
from gitmem.core.models import DiffStats


class DiffEngine:
    """Computes differences between GitMem cognitive states."""
    
    def __init__(self, object_store: ObjectStore):
        self.store = object_store

    def diff_trees(self, tree_a_sha: str, tree_b_sha: str) -> Dict[str, Any]:
        """
        Compare two cognitive trees and return the differences.
        tree_a is usually the older/base tree, tree_b is the newer one.
        """
        if tree_a_sha == tree_b_sha:
            return {"added": [], "modified": [], "deleted": []}

        tree_a = self.store.get_tree(tree_a_sha) if tree_a_sha else CognitiveTree()
        tree_b = self.store.get_tree(tree_b_sha) if tree_b_sha else CognitiveTree()
        
        if not tree_a and tree_a_sha:
            raise ValueError(f"Tree A not found: {tree_a_sha}")
        if not tree_b and tree_b_sha:
            raise ValueError(f"Tree B not found: {tree_b_sha}")

        # Map by logical path
        entries_a = {entry.path: entry for entry in tree_a.entries}
        entries_b = {entry.path: entry for entry in tree_b.entries}
        
        added = []
        modified = []
        deleted = []
        
        # Check added and modified
        for path, entry_b in entries_b.items():
            entry_a = entries_a.get(path)
            if not entry_a:
                added.append(entry_b.to_dict())
            elif entry_a.sha != entry_b.sha:
                modified.append({
                    "path": path,
                    "old_sha": entry_a.sha,
                    "new_sha": entry_b.sha,
                    "name": entry_b.name,
                    "mode": entry_b.mode
                })
                
        # Check deleted
        for path, entry_a in entries_a.items():
            if path not in entries_b:
                deleted.append(entry_a.to_dict())
                
        return {
            "added": added,
            "modified": modified,
            "deleted": deleted
        }

    def diff_commits(self, commit_a_sha: str, commit_b_sha: str) -> Dict[str, Any]:
        """Compare two commits by comparing their root trees."""
        commit_a = self.store.get_commit(commit_a_sha) if commit_a_sha else None
        commit_b = self.store.get_commit(commit_b_sha)
        
        if not commit_b:
            raise ValueError(f"Commit B not found: {commit_b_sha}")
            
        tree_a_sha = commit_a.tree_sha if commit_a else None
        tree_b_sha = commit_b.tree_sha
        
        return self.diff_trees(tree_a_sha, tree_b_sha)

    def compute_stats(self, diff_result: Dict[str, Any]) -> DiffStats:
        """Convert a diff result into numerical stats."""
        return DiffStats(
            added=len(diff_result.get("added", [])),
            modified=len(diff_result.get("modified", [])),
            deleted=len(diff_result.get("deleted", [])),
            changes=diff_result
        )
