"""
GitMem v2.0 — VCS Orchestrator

Facade for the entire Version Control Layer.
Coordinates Object Store, Branch Manager, Merge Engine, Diff Engine, and RefLog.
Replaces the old MemoryStore, separating pure VCS logic from storage connections.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from gitmem.core.vcs.object_store import ObjectStore, MemoryCommit, CognitiveTree, TreeEntry, MemoryBlob
from gitmem.core.vcs.branch_manager import BranchManager
from gitmem.core.vcs.merge_engine import MergeEngine, MergePolicy
from gitmem.core.vcs.diff_engine import DiffEngine
from gitmem.core.vcs.reflog import RefLog


class VCSOrchestrator:
    """
    Central orchestrator for GitMem version control semantics.
    Handles commits, branches, merges, and rollbacks.
    """
    
    def __init__(self, supabase_client, object_store: ObjectStore):
        self.client = supabase_client
        self.store = object_store
        
        # Initialize sub-components
        self.reflog = RefLog(self.client)
        self.branch_manager = BranchManager(self.client, self.reflog)
        self.diff_engine = DiffEngine(self.store)
        self.merge_engine = MergeEngine(self.store, self.diff_engine)
        
        self._table_commits = "gitmem_commits"

    def _persist_commit_metadata(self, commit: MemoryCommit, workspace_id: str) -> None:
        """Save commit metadata to Postgres for fast querying."""
        if not self.client:
            return
            
        data = {
            "hash": commit.sha,
            "repo_id": commit.agent_id,  # MemoryCommit stores repo_id in agent_id field
            "workspace_id": workspace_id,
            "agent_id": commit.author,   # The actual actor who made the commit
            "author_id": commit.author,
            "message": commit.message,
            "parents": commit.parents,
            "tree_hash": commit.tree_sha,
            "stats": commit.stats,
            "timestamp": commit.timestamp
        }
        
        try:
            self.client.table(self._table_commits).insert(data).execute()
        except Exception as e:
            # Might already exist
            if "Duplicate" not in str(e):
                print(f"[VCS] Failed to persist commit metadata: {e}")

    def commit(self, repo_id: str, workspace_id: str, author_id: str, message: str, 
               memory_blobs: List[MemoryBlob], branch: str = "main") -> Dict[str, Any]:
        """
        Create a new commit from a list of memory blobs on a specific branch.
        """
        # 1. Store blobs and build the tree
        tree = CognitiveTree()
        memory_ids = []
        
        for i, blob in enumerate(memory_blobs):
            sha = self.store.store_blob(blob)
            path = f"{blob.memory_type}/{sha}"
            
            entry = TreeEntry(
                mode=blob.memory_type,
                sha=sha,
                path=path,
                name=f"Memory {sha[:8]}"
            )
            tree.add_entry(entry)
            if hasattr(blob, "id"):
                memory_ids.append(blob.id)
                
        # 2. Get current branch head
        branch_ref = self.branch_manager.get_branch(repo_id, branch)
        parents = [branch_ref["target_hash"]] if branch_ref else []
        
        # 3. Store Tree
        tree_sha = self.store.store_tree(tree)
        
        # 4. Create and store Commit
        commit = MemoryCommit(
            tree_sha=tree_sha,
            message=message,
            author=author_id,
            agent_id=repo_id,
            parents=parents
        )
        
        commit_sha = self.store.store_commit(commit)
        
        # 5. Calculate diff stats against parent
        if parents:
            diff = self.diff_engine.diff_commits(parents[0], commit_sha)
            commit.stats = self.diff_engine.compute_stats(diff).model_dump()
        else:
            commit.stats = {"added": len(tree.entries), "modified": 0, "deleted": 0}
            
        # 6. Persist metadata & update branch
        self._persist_commit_metadata(commit, workspace_id)
        
        if not branch_ref:
            self.branch_manager.create_branch(repo_id, branch, commit_sha, author_id)
        else:
            self.branch_manager.update_branch(repo_id, branch, commit_sha, author_id, action="commit")
            
        return {
            "status": "success",
            "commit_hash": commit_sha,
            "tree_hash": tree_sha,
            "stats": commit.stats
        }

    def branch(self, repo_id: str, branch_name: str, target_branch_or_hash: str, actor_id: str) -> bool:
        """Create a new branch from an existing branch or commit hash."""
        # Check if target is a branch name
        target_ref = self.branch_manager.get_branch(repo_id, target_branch_or_hash)
        target_hash = target_ref["target_hash"] if target_ref else target_branch_or_hash
        
        return self.branch_manager.create_branch(repo_id, branch_name, target_hash, actor_id)

    def merge(self, repo_id: str, target_branch: str, source_branch: str, actor_id: str, 
              workspace_id: str, policy: MergePolicy = MergePolicy.LAST_WRITE_WINS) -> Dict[str, Any]:
        """Merge source_branch into target_branch."""
        target_ref = self.branch_manager.get_branch(repo_id, target_branch)
        source_ref = self.branch_manager.get_branch(repo_id, source_branch)
        
        if not target_ref or not source_ref:
            return {"status": "error", "error": "Branch not found"}
            
        target_sha = target_ref["target_hash"]
        source_sha = source_ref["target_hash"]
        
        # Find common ancestor (simplified: assuming target parent for now, a real implementation needs LCA)
        base_sha = None # TODO: Implement Lowest Common Ancestor
        
        try:
            # 1. Merge trees
            target_commit = self.store.get_commit(target_sha)
            source_commit = self.store.get_commit(source_sha)
            
            merged_tree_sha = self.merge_engine.merge_trees(
                base_sha=base_sha, 
                target_sha=target_commit.tree_sha if target_commit else None, 
                source_sha=source_commit.tree_sha if source_commit else None,
                policy=policy
            )
            
            # 2. Create merge commit
            merge_commit = MemoryCommit(
                tree_sha=merged_tree_sha,
                message=f"Merge branch '{source_branch}' into '{target_branch}'",
                author=actor_id,
                agent_id=repo_id,
                parents=[target_sha, source_sha]
            )
            
            commit_sha = self.store.store_commit(merge_commit)
            self._persist_commit_metadata(merge_commit, workspace_id)
            
            # 3. Update target branch
            self.branch_manager.update_branch(repo_id, target_branch, commit_sha, actor_id, action="merge")
            
            return {
                "status": "success",
                "commit_hash": commit_sha
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def rollback(self, repo_id: str, branch_name: str, target_hash: str, actor_id: str) -> bool:
        """Hard reset a branch to a previous commit."""
        return self.branch_manager.update_branch(repo_id, branch_name, target_hash, actor_id, action="rollback")

    def cherry_pick(self, repo_id: str, branch_name: str, commit_sha: str, actor_id: str, 
                    workspace_id: str, policy: MergePolicy = MergePolicy.LAST_WRITE_WINS) -> Dict[str, Any]:
        """Apply the changes from a single commit to the current branch."""
        branch_ref = self.branch_manager.get_branch(repo_id, branch_name)
        if not branch_ref:
            return {"status": "error", "error": f"Branch {branch_name} not found"}
            
        current_sha = branch_ref["target_hash"]
        current_commit = self.store.get_commit(current_sha)
        
        try:
            new_tree_sha = self.merge_engine.cherry_pick(commit_sha, current_commit.tree_sha if current_commit else None, policy)
            
            new_commit = MemoryCommit(
                tree_sha=new_tree_sha,
                message=f"Cherry-pick {commit_sha[:8]}",
                author=actor_id,
                agent_id=repo_id,
                parents=[current_sha]
            )
            
            new_commit_sha = self.store.store_commit(new_commit)
            self._persist_commit_metadata(new_commit, workspace_id)
            
            self.branch_manager.update_branch(repo_id, branch_name, new_commit_sha, actor_id, action="cherry-pick")
            
            return {"status": "success", "commit_hash": new_commit_sha}
        except Exception as e:
            return {"status": "error", "error": str(e)}
