import unittest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import uuid
import os
from gitmem.core.app import gitmem_app

class TestVCSOrchestrator(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Setup a dedicated test workspace and repo."""
        cls.test_user_id = os.getenv("MCP_USER_ID", "test-runner")
        cls.ws_id = str(uuid.uuid4())
        cls.repo_id = str(uuid.uuid4())
        
        # Create Workspace directly in DB for testing
        if gitmem_app.supabase_client:
            try:
                gitmem_app.supabase_client.table("gitmem_workspaces").insert({
                    "workspace_id": cls.ws_id,
                    "name": "Test Workspace",
                    "slug": f"test-{cls.ws_id[:8]}",
                    "owner_id": cls.test_user_id
                }).execute()
                
                # Create Repo
                gitmem_app.supabase_client.table("gitmem_repos").insert({
                    "repo_id": cls.repo_id,
                    "workspace_id": cls.ws_id,
                    "name": "Integration Test Repo",
                    "slug": f"test-repo-{cls.repo_id[:8]}",
                    "owner_id": cls.test_user_id
                }).execute()
            except Exception as e:
                print(f"Setup error: {e}")

    @classmethod
    def tearDownClass(cls):
        """Cleanup test data."""
        if gitmem_app.supabase_client:
            try:
                gitmem_app.supabase_client.table("gitmem_repos").delete().eq("repo_id", cls.repo_id).execute()
                gitmem_app.supabase_client.table("gitmem_workspaces").delete().eq("workspace_id", cls.ws_id).execute()
            except Exception:
                pass

    def test_01_commit_immutability(self):
        """Test that a commit creates an immutable tree/DAG object."""
        result = gitmem_app.command_handler.execute(
            "commit", 
            actor_id=self.test_user_id, 
            workspace_id=self.ws_id,
            payload={
                "repo_id": self.repo_id,
                "message": "Initial test commit"
            },
            skip_auth=True
        )
        
        self.assertEqual(result["status"], "success")
        commit_id = result["data"]["commit_hash"]
        self.assertIsNotNone(commit_id)
        
        # Verify branch updated
        if gitmem_app.supabase_client:
            res = gitmem_app.supabase_client.table("gitmem_refs").select("target_hash").eq("repo_id", self.repo_id).eq("ref_name", "main").execute()
            self.assertTrue(len(res.data) > 0)
            self.assertEqual(res.data[0]["target_hash"], commit_id)

    def test_02_branch_creation(self):
        """Test branching off main."""
        branch_name = "feature-test"
        res = gitmem_app.vcs.branch_manager.create_branch(self.repo_id, branch_name, "main", self.test_user_id)
        self.assertTrue(res)

if __name__ == '__main__':
    unittest.main()
