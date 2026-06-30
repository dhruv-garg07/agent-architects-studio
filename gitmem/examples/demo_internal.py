"""
Demo script for GitMem v2.

This script demonstrates how to:
1. Ingest memories via the IngestionPipeline
2. Query memories via the RetrievalOrchestrator
3. Commit memory state via the VCSOrchestrator

NOTE: The v1 `MemoryStore` class was removed in the v2 refactor.
Its functionality is split across:
  - gitmem.core.retrieval.ingestion.IngestionPipeline  (add/store memories)
  - gitmem.core.retrieval.retrieval.RetrievalOrchestrator (query/search)
  - gitmem.core.vcs.vcs_orchestrator.VCSOrchestrator  (commit/branch/merge)
  - gitmem.core.app.gitmem_app  (the singleton that wires everything together)

For the simplest usage, run the Flask dev server and use the SDK:
  from gitmem.sdk.client import GitMem
  mem = GitMem(api_url="http://localhost:5000")
  mem.add("The user prefers dark mode.", agent_id="agent_007")
  results = mem.query("user preferences", agent_id="agent_007")
"""

import sys
import os

# Add root to path so we can import gitmem if running locally without install
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def run_demo():
    print("--- GITMEM INTERNAL DEMO (v2) ---")
    print()
    print("The v1 MemoryStore class was removed in the v2 architecture refactor.")
    print()
    print("To run a live demo use the GitMem SDK client after starting the server:")
    print()
    print("  from gitmem.sdk.client import GitMem")
    print("  mem = GitMem(api_url='http://localhost:5000')")
    print("  mem.add('The user prefers dark mode.', agent_id='agent_007')")
    print("  results = mem.query('user preferences', agent_id='agent_007')")
    print("  mem.commit(message='Initial memory sync', agent_id='agent_007')")
    print()
    print("Or use the full v2 API directly for a server-less integration test:")
    print()

    try:
        from gitmem.core.app import gitmem_app
        from gitmem.core.vcs.object_store import MemoryBlob

        agent_id = "agent_007"

        # Add memory blobs via VCS orchestrator
        blobs = [
            MemoryBlob(content="The user prefers dark mode.", memory_type="episodic", importance=0.7),
            MemoryBlob(content="Project deadline is Friday.", memory_type="episodic", importance=0.9),
        ]

        result = gitmem_app.vcs.commit(
            repo_id=agent_id,
            workspace_id="default",
            author_id="demo_user",
            message="Initial memory sync (demo)",
            memory_blobs=blobs,
        )

        print(f"Commit result: {result}")
        print("\n--- DEMO COMPLETE ---")

    except Exception as exc:
        print(f"[Demo] Could not run live demo (check server config / env vars): {exc}")
        print("See README.md or USER_GUIDE.md for full setup instructions.")


if __name__ == "__main__":
    run_demo()
