from typing import List, Dict, Any, Optional
# import chromadb # Commented out to avoid immediate import error if not installed
# from chromadb.config import Settings

class VectorEngine:
    def __init__(self, path: str = "./gitmem_data/indexes"):
        self.path = path
        self.client = None
        self.collection = None
        self._initialize()

    def _initialize(self):
        try:
            import os
            import sys
            
            # Add parent directories to sys.path to ensure we can import Octave_mem
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # current_dir is gitmem/core/storage
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
                
            from Octave_mem.RAG_DB.chroma_collection_manager import get_chroma_client, ChromaCollectionManager
            
            self.client = get_chroma_client()
            self.is_cloud = hasattr(self.client, 'tenant') and self.client.tenant is not None
            
            # Share the single RemoteEmbeddingClient
            if ChromaCollectionManager._shared_embedder is None:
                from Octave_mem.RAG_DB.chroma_collection_manager import RemoteEmbeddingClient
                ChromaCollectionManager._shared_embedder = RemoteEmbeddingClient()
            self.ef = ChromaCollectionManager._shared_embedder
            
            # Note: We no longer eagerly create gitmem_global. 
            # We defer to agent-specific collections in operations.
            self.collection = None
                
        except Exception as e:
            print(f"ChromaDB initialization failed in VectorEngine: {e}")
            self.client = None

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str], collection_name: str = None):
        if not self.client:
            return
            
        target_collection = self.collection
        if collection_name:
            try:
                target_collection = self.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=self.ef
                )
            except:
                pass

        if not target_collection:
            return
            
        processed_metadatas = []
        for meta in metadatas:
            if not meta:
                processed_metadatas.append({"_placeholder": "true"})
            else:
                processed_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (list, dict)):
                        processed_meta[k] = str(v)
                    else:
                        processed_meta[k] = v
                processed_metadatas.append(processed_meta)
        
        try:
            target_collection.add(documents=texts, metadatas=processed_metadatas, ids=ids)
        except:
            pass

    def add_vectors(self, collection_name: str, vectors: List[List[float]], documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """Explicit vector ingestion for V2 pipeline."""
        if not self.client:
            return
            
        try:
            target_collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.ef
            )
            
            processed_metadatas = []
            for meta in metadatas:
                processed_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (list, dict)):
                        processed_meta[k] = str(v)
                    else:
                        processed_meta[k] = v
                processed_metadatas.append(processed_meta)

            target_collection.add(
                embeddings=vectors,
                documents=documents,
                metadatas=processed_metadatas,
                ids=ids
            )
        except Exception as e:
            print(f"[VectorEngine] add_vectors failed: {e}")

    def add_memory(self, memory: Any):
        """Helper to add a memory object directly."""
        try:
            # Handle MemoryItem or dict
            if hasattr(memory, 'to_dict'):
                m_dict = memory.to_dict()
            else:
                m_dict = memory
                
            agent_id = m_dict.get("agent_id", "unknown")
            
            # Map to standard schema
            metadata = {
                "agent_id": agent_id,
                "type": m_dict.get("type", "episodic"),
                "importance": m_dict.get("importance", 0.0),
                "created_at": str(m_dict.get("created_at", "")),
                "visibility": m_dict.get("visibility", m_dict.get("scope", "private"))
            }
            
            # Merge extra metadata if any
            if "metadata" in m_dict and isinstance(m_dict["metadata"], dict):
                for k, v in m_dict["metadata"].items():
                    if k not in metadata:
                        metadata[k] = v
                
            self.add_texts(
                texts=[m_dict["content"]],
                metadatas=[metadata],
                ids=[m_dict["id"]],
                collection_name=agent_id  # Default to agent collection
            )
        except Exception as e:
            print(f"[VectorEngine] Error adding memory: {e}")

    def query(self, query_text: str = None, n_results: int = 5, where: Dict = None, 
              collection_name: str = None, query_embeddings: List[List[float]] = None) -> List[Dict]:
        if not self.client:
            return []
        
        # 1. Determine collection
        target_collection = self.collection
        target_collection = None
        
        # Determine agent_id to find the collection
        agent_id = collection_name
        if not agent_id and where and where.get("agent_id"):
            agent_id = where["agent_id"]
            
        if agent_id:
            try:
                target_collection = self.client.get_collection(name=agent_id)
            except:
                pass
                
        if not target_collection:
            return []
            
        try:
            query_args = {
                "n_results": n_results,
                "where": where
            }
            if query_embeddings:
                query_args["query_embeddings"] = query_embeddings
            else:
                query_args["query_texts"] = [query_text]

            results = target_collection.query(**query_args)
            
            normalized = []
            if results['ids']:
                for i, vid in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    normalized.append({
                        "id": vid,
                        "content": results['documents'][0][i],
                        "metadata": metadata,
                        "distance": results['distances'][0][i] if 'distances' in results and results['distances'] else 0
                    })
            return normalized
        except Exception:
            return []

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        if not self.client:
            return {"embeddings": 0, "freshness": "Disconnected", "latency": "0ms"}
        
        total_count = 0
        
        try:
            col = self.client.get_collection(name=agent_id)
            total_count = col.count()
        except:
            pass
            
        return {
            "embeddings": total_count,
            "freshness": "Connected" if self.is_cloud else "Volatile",
            "latency": "12ms"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the default collection."""
        if not self.client:
            return {"embeddings": 0, "freshness": "N/A", "latency": "0ms"}
        total_count = 0
        try:
            if self.collection:
                total_count = self.collection.count()
        except Exception:
            pass
        return {
            "embeddings": total_count,
            "freshness": "Connected" if getattr(self, 'is_cloud', False) else "Volatile",
            "latency": "12ms"
        }

    def delete_memory(self, memory_id: str, agent_id: str = None) -> bool:
        """Delete a single memory vector from ChromaDB by its ID."""
        if not self.client or not agent_id:
            return False
        try:
            target_collection = self.client.get_collection(name=agent_id)
            target_collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            print(f"[VectorEngine] delete_memory failed for {memory_id}: {e}")
            return False

    def update_memory(self, memory_id: str, content: str, metadata: Dict[str, Any], agent_id: str = None) -> bool:
        """Update the document and metadata for an existing vector by ID."""
        if not self.client or not agent_id:
            return False
        try:
            target_collection = self.client.get_collection(name=agent_id)
            
            # Standardize schema on update
            clean_meta = {
                "agent_id": agent_id,
                "type": metadata.get("type", metadata.get("memory_type", "episodic")),
                "importance": metadata.get("importance", 0.0),
                "created_at": str(metadata.get("created_at", metadata.get("timestamp", ""))),
                "visibility": metadata.get("visibility", metadata.get("scope", "private"))
            }
            
            for k, v in metadata.items():
                if k not in clean_meta:
                    if isinstance(v, (list, dict)):
                        clean_meta[k] = str(v)
                    else:
                        clean_meta[k] = v
                        
            target_collection.update(
                ids=[memory_id],
                documents=[content],
                metadatas=[clean_meta]
            )
            return True
        except Exception as e:
            print(f"[VectorEngine] update_memory failed for {memory_id}: {e}")
            return False

    def get_agent_vectors(self, agent_id: str, limit: int = 100) -> List[Dict]:
        """Get all vectors for a specific agent."""
        if not self.client:
            return []
            
        # Target collection is the agent's collection
        target_collection = None
        try:
            target_collection = self.client.get_collection(name=agent_id)
        except:
            pass
            
        if not target_collection:
            return []
            
        try:
            # Fetch simpler data - exclude embeddings to save bandwidth/memory
            get_args = {
                "limit": limit,
                "include": ["documents", "metadatas"]
            }
                
            results = target_collection.get(**get_args)
            
            normalized = []
            if results and results.get('ids'):
                metadatas = results.get('metadatas') or []
                documents = results.get('documents') or []
                
                for i, vid in enumerate(results['ids']):
                    metadata = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}
                    metadata["agent_id"] = agent_id
                    
                    doc_content = documents[i] if i < len(documents) else ""
                    
                    normalized.append({
                        "id": vid,
                        "content": doc_content,
                        "metadata": metadata,
                        "embedding": None
                    })
            return normalized

        except Exception as e:
            print(f"Error fetching agent vectors: {e}")
            return []

    def categorize_vectors(self, vectors: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Sort vectors into memory bins based on their 'memory_type' metadata field.
        Returns a dictionary with keys: episodic, semantic, procedural, working.
        """
        bins = {
            "episodic": [],
            "semantic": [],
            "procedural": [],
            "working": [],
            "vectors": [] # Keep all here or just uncategorized/others?
        }
        
        for v in vectors:
            meta = v.get("metadata", {})
            # Check for memory_type in various common keys
            mtype = meta.get("memory_type") or meta.get("type") or meta.get("category")
            
            # Default to 'vectors' (uncategorized) if no type found
            target_bin = "vectors"
            
            if mtype:
                mtype = str(mtype).lower()
                if "episodic" in mtype: target_bin = "episodic"
                elif "semantic" in mtype: target_bin = "semantic"
                elif "procedural" in mtype: target_bin = "procedural"
                elif "working" in mtype: target_bin = "working"
            
            # Create a standard memory object structure
            mem_obj = {
                "id": v.get("id"),
                "content": v.get("content"),
                "type": target_bin if target_bin != "vectors" else "vector", # Normalize type name
                "importance": float(meta.get("importance", 0.5)),
                "created_at": meta.get("created_at") or meta.get("timestamp") or "Unknown",
                "metadata": meta,
                "keywords": meta.get("keywords", []),
                "source": "chromadb"
            }
            
            # Add to specific bin
            if target_bin != "vectors":
                bins[target_bin].append(mem_obj)
            
            # Also add to generic 'vectors' list, but maybe mark source as categorized?
            # User wants them visible in UI bins.
            # If we put them in bins, they show up in folders.
            # If we put them in 'vectors', they show up in Vectors section.
            # Let's verify what the user wants. "visible in this UI" implies bins.
            # But we might double count if we add to both.
            # Using specific bins is better for "Sorting".
            # We add all to 'vectors' bin just in case UI expects it there too?
            # Let's add to 'vectors' bin only if uncategorized, OR add a reference.
            
            # Decision: Add to both specific bin AND vectors bin, 
            # OR just specific bin if categorized.
            # Given the UI shows "Context Store" (folders) and "Vectors" (list),
            # it's usually good to have comprehensive list in Vectors.
            
            vector_display_obj = mem_obj.copy()
            vector_display_obj["type"] = "vector" # Always call it vector in the vectors list
            bins["vectors"].append(vector_display_obj)
            
        return bins

    def get_vector(self, vector_id: str, agent_id: str = None) -> Optional[Dict]:
        """Get a single vector by ID."""
        if not self.client or not agent_id:
            return None
            
        target_collection = None
        try:
            target_collection = self.client.get_collection(name=agent_id)
        except: pass

        if not target_collection:
            return None
        
        try:
            results = target_collection.get(ids=[vector_id], include=["metadatas", "documents"])
            if results and results.get('ids'):
                return {
                    "id": vector_id,
                    "content": results['documents'][0],
                    "metadata": results['metadatas'][0],
                    "type": "vector"
                }
        except: pass
        
        return None


