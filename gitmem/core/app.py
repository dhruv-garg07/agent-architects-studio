"""
GitMem v2.0 — App Factory

Bootstraps all the singletons and dependencies for the GitMem core.
Provides a unified entry point for API routes and MCP servers to get
access to the initialized Command Handler and Orchestrators.
"""

import os
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from supabase import create_client

from gitmem.core.storage.supabase_connector import SupabaseConnector
from gitmem.core.storage.vector_engine import VectorEngine
from gitmem.core.storage.cache import ObjectCache

from gitmem.core.events.event_bus import event_bus
from gitmem.core.events.event_store import EventStore
from gitmem.core.events.command_handler import CommandHandler

from gitmem.core.access.workspace import WorkspaceManager
from gitmem.core.access.auth import AuthService
from gitmem.core.access.rbac import RBACEngine

from gitmem.core.vcs.object_store import ObjectStore
from gitmem.core.vcs.vcs_orchestrator import VCSOrchestrator

from gitmem.core.retrieval.retrieval import RetrievalOrchestrator
from gitmem.core.retrieval.ingestion import IngestionPipeline


class GitMemApp:
    """Singleton holding all initialized GitMem v2.0 services."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GitMemApp, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        """Initialize all GitMem core services."""
        print("[GitMem] Bootstrapping V2 Core Services...")
        
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        
        # 1. Supabase Connection
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            self.supabase_client = create_client(supabase_url, supabase_key)
        else:
            print("Warning: Supabase credentials not found. DB features disabled.")
            self.supabase_client = None
            
        # 2. Vector DB
        self.vector_engine = VectorEngine()
        
        # 3. Storage & Cache
        self.cache = ObjectCache()
        self.object_store = ObjectStore(self.supabase_client, cache=self.cache)
        
        # 4. Access Layer
        self.workspace_manager = WorkspaceManager(self.supabase_client)
        self.auth_service = AuthService(self.supabase_client)
        self.rbac_engine = RBACEngine(self.workspace_manager, self.supabase_client)
        
        # 5. Events Layer
        self.event_store = EventStore(self.supabase_client)
        self.event_bus = event_bus # global singleton
        
        # 6. VCS Layer
        self.vcs = VCSOrchestrator(self.supabase_client, self.object_store)
        
        # 7. Retrieval / Ingestion Layer
        self.retrieval = RetrievalOrchestrator(self.supabase_client, self.vector_engine)
        self.ingestion = IngestionPipeline(self.supabase_client, self.vector_engine, self.event_bus)
        
        # 8. Command Handler (The Spine)
        self.command_handler = CommandHandler(
            event_bus=self.event_bus,
            event_store=self.event_store,
            auth=self.auth_service,
            rbac=self.rbac_engine
        )
        
        # Register Commands
        self._register_commands()
        
    def _register_commands(self):
        """Map command strings to underlying service methods."""
        # --- Workspace Commands ---
        def create_workspace_cmd(actor_id, workspace_id, name, slug, plan="free"):
            return self.workspace_manager.create_workspace(name=name, slug=slug, owner_id=actor_id, plan=plan)
        self.command_handler.register("create_workspace", create_workspace_cmd)
        
        # --- Memory/Ingestion Commands ---
        def add_memory(actor_id, workspace_id, repo_id, text, metadata=None):
            items = self.ingestion.process_raw_input(repo_id, workspace_id, actor_id, text, metadata)
            return {"memories_added": len(items)}
        self.command_handler.register("add_memory", add_memory)
        
        # --- Retrieval Commands ---
        def retrieve_context(actor_id, workspace_id, repo_id, query, max_tokens=4000):
            return self.retrieval.retrieve(query, repo_id, actor_id, max_tokens)
        self.command_handler.register("retrieve_context", retrieve_context)
        
        # --- VCS Commands ---
        def commit(actor_id, workspace_id, repo_id, message, branch="main"):
            # A full command would gather staging area. Here we pass empty blobs for stub.
            # In reality, ingestion handles memory blobs, and commit snapshots the current DAG.
            return self.vcs.commit(repo_id, workspace_id, actor_id, message, [], branch)
        self.command_handler.register("commit", commit)


# Global access to the bootstrapped app
gitmem_app = GitMemApp()
