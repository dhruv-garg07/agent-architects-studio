import unittest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import uuid
import os
from gitmem.core.app import gitmem_app

class TestRetrievalPipeline(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_user_id = os.getenv("MCP_USER_ID", "test-runner")
        cls.ws_id = str(uuid.uuid4())
        cls.repo_id = str(uuid.uuid4())
        
        if gitmem_app.supabase_client:
            try:
                gitmem_app.supabase_client.table("gitmem_workspaces").insert({
                    "workspace_id": cls.ws_id,
                    "name": "Retrieval Test Workspace",
                    "slug": f"ret-{cls.ws_id[:8]}",
                    "owner_id": cls.test_user_id
                }).execute()
                
                gitmem_app.supabase_client.table("gitmem_repos").insert({
                    "repo_id": cls.repo_id,
                    "workspace_id": cls.ws_id,
                    "name": "Retrieval Test Repo",
                    "slug": f"ret-repo-{cls.repo_id[:8]}",
                    "owner_id": cls.test_user_id
                }).execute()
            except Exception as e:
                print(f"Setup error: {e}")

    @classmethod
    def tearDownClass(cls):
        if gitmem_app.supabase_client:
            try:
                gitmem_app.supabase_client.table("gitmem_repos").delete().eq("repo_id", cls.repo_id).execute()
                gitmem_app.supabase_client.table("gitmem_workspaces").delete().eq("workspace_id", cls.ws_id).execute()
            except Exception:
                pass

    def test_01_ingestion_and_retrieval(self):
        """Test full pipeline: Ingest memory, then retrieve it."""
        # 1. Ingest
        text = "GitMem uses ChromaDB for semantic vector search."
        res = gitmem_app.command_handler.execute(
            "add_memory",
            actor_id=self.test_user_id,
            workspace_id=self.ws_id,
            payload={
                "repo_id": self.repo_id,
                "text": text,
                "metadata": {"source": "test_case"}
            },
            skip_auth=True
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["data"]["memories_added"] > 0)
        
        # 2. Retrieve
        ret_res = gitmem_app.command_handler.execute(
            "retrieve_context",
            actor_id=self.test_user_id,
            workspace_id=self.ws_id,
            payload={
                "repo_id": self.repo_id,
                "query": "What database does GitMem use for vectors?",
                "max_tokens": 1000
            },
            skip_auth=True
        )
        
        self.assertEqual(ret_res["status"], "success")
        context = ret_res["data"]["context_string"]
        self.assertIn("ChromaDB", context)

if __name__ == '__main__':
    unittest.main()
