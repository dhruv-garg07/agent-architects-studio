"""
GitMem v2.0 — Ingestion Pipeline

Orchestrates the processing of raw data into structured, embedded, and classified memories.
Pipeline: Raw Input -> Chunker -> Classifier -> Embedder -> Deduplicator -> Store.
"""

from typing import Dict, Any, List, Optional
from gitmem.core.retrieval.chunker import Chunker
from gitmem.core.retrieval.classifier import Classifier
from gitmem.core.retrieval.embedder import Embedder
from gitmem.core.models import MemoryItem, MemoryType, Visibility
from gitmem.core.events.event_bus import emit_memory_created


class IngestionPipeline:
    """Processes raw data into persistent memory items."""
    
    def __init__(self, supabase_client, chroma_adapter, event_bus=None):
        self.client = supabase_client
        self.vector_store = chroma_adapter
        self.chunker = Chunker()
        self.classifier = Classifier()
        self.embedder = Embedder()
        self.event_bus = event_bus
        self._table = "gitmem_memories"

    def _ensure_repo(self, repo_id: str, workspace_id: str):
        """Ensure a repo exists before inserting dependent records."""
        if not self.client: return
        try:
            res = self.client.table("gitmem_repos").select("repo_id").eq("repo_id", repo_id).execute()
            if not res.data:
                # Provision workspace
                ws_res = self.client.table("gitmem_workspaces").select("workspace_id").eq("workspace_id", workspace_id).execute()
                if not ws_res.data:
                    try:
                        self.client.table("gitmem_workspaces").insert({
                            "workspace_id": workspace_id,
                            "name": "Default Workspace",
                            "slug": workspace_id,
                            "owner_id": "system"
                        }).execute()
                    except: pass
                
                # Provision repo
                self.client.table("gitmem_repos").insert({
                    "repo_id": repo_id,
                    "workspace_id": workspace_id,
                    "name": f"Agent {repo_id[:8]}",
                    "slug": repo_id,
                    "owner_id": "system"
                }).execute()
        except Exception as e:
            print(f"[Ingestion] Warning: Could not ensure repo {repo_id} exists: {e}")

    def process_raw_input(self, repo_id: str, workspace_id: str, agent_id: str, 
                          text: str, metadata: Dict[str, Any] = None) -> List[MemoryItem]:
        """
        Process a raw string of text into one or more MemoryItems.
        Typically called asynchronously by a worker for large texts.
        """
        if not text.strip():
            return []
            
        # 1. Chunking
        chunks = self.chunker.chunk_text(text, metadata)
        
        results = []
        for chunk in chunks:
            chunk_text = chunk["text"]
            chunk_meta = chunk["metadata"]
            
            # 2. Classification
            m_type, importance, tags = self.classifier.classify(chunk_text, chunk_meta)
            
            # 3. Embedding
            embedding = self.embedder.embed(chunk_text)
            
            # 4. Create Memory Item
            item = MemoryItem(
                repo_id=repo_id,
                workspace_id=workspace_id,
                agent_id=agent_id,
                type=m_type,
                content=chunk_text,
                importance=importance,
                tags=tags,
                metadata=chunk_meta,
                embedding=embedding
            )
            
            # 5. Persist
            self._persist_item(item)
            results.append(item)
            
        return results

    def _persist_item(self, item: MemoryItem) -> None:
        """Save memory item to Supabase and ChromaDB."""
        # 1. Save metadata to Supabase
        if self.client:
            try:
                self._ensure_repo(item.repo_id, item.workspace_id)
                self.client.table(self._table).insert(item.to_dict()).execute()
            except Exception as e:
                print(f"[Ingestion] Supabase insert failed: {e}")
                
        # 2. Save vector to ChromaDB
        if self.vector_store and item.embedding:
            try:
                self.vector_store.add_vectors(
                    collection_name=item.agent_id, # Using agent_id as collection name
                    vectors=[item.embedding],
                    documents=[item.content],
                    metadatas=[{"id": item.id, "type": item.type.value}],
                    ids=[item.id]
                )
            except Exception as e:
                print(f"[Ingestion] ChromaDB insert failed: {e}")
                
        # 3. Emit event
        if self.event_bus:
            emit_memory_created(
                agent_id=item.agent_id,
                memory_id=item.id,
                memory_type=item.type.value,
                content=item.content,
                workspace_id=item.workspace_id,
                visibility=item.visibility.value
            )
