import unittest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import uuid
import os
from gitmem.core.app import gitmem_app
from gitmem.core.models import WorkspaceRole

class TestRBAC(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_user_id = os.getenv("MCP_USER_ID", "test-runner")
        cls.ws_id = str(uuid.uuid4())
        
        if gitmem_app.supabase_client:
            try:
                gitmem_app.supabase_client.table("gitmem_workspaces").insert({
                    "workspace_id": cls.ws_id,
                    "name": "RBAC Test Workspace",
                    "slug": f"rbac-{cls.ws_id[:8]}",
                    "owner_id": cls.test_user_id,
                    "plan": "free"
                }).execute()
                
                # Add test user as MEMBER
                gitmem_app.supabase_client.table("gitmem_workspace_members").insert({
                    "workspace_id": cls.ws_id,
                    "user_id": cls.test_user_id,
                    "role": WorkspaceRole.MEMBER.value
                }).execute()
            except Exception as e:
                print(f"Setup error: {e}")

    @classmethod
    def tearDownClass(cls):
        if gitmem_app.supabase_client:
            try:
                gitmem_app.supabase_client.table("gitmem_workspace_members").delete().eq("workspace_id", cls.ws_id).execute()
                gitmem_app.supabase_client.table("gitmem_workspaces").delete().eq("workspace_id", cls.ws_id).execute()
            except Exception:
                pass

    def test_01_workspace_isolation(self):
        """Test isolation across mismatched workspaces."""
        has_access = gitmem_app.rbac_engine.check_permission(self.test_user_id, "fake_ws_id", "workspace:create_repo")
        self.assertFalse(has_access)

    def test_02_role_permissions(self):
        """Test member cannot delete workspace but can create repo."""
        can_delete = gitmem_app.rbac_engine.check_permission(self.test_user_id, self.ws_id, "workspace:delete")
        self.assertFalse(can_delete)
        
        can_create = gitmem_app.rbac_engine.check_permission(self.test_user_id, self.ws_id, "workspace:create_repo")
        self.assertTrue(can_create)

    def test_03_quota_enforcement(self):
        """Test the free plan limits."""
        # Free plan max_repos is 3
        can_add = gitmem_app.rbac_engine.check_quota(self.ws_id, "repos", increment=4)
        self.assertFalse(can_add)

if __name__ == '__main__':
    unittest.main()
