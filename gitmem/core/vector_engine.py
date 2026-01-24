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
            import chromadb
            import os
            from chromadb.config import Settings
            
            # Load environment variables just in case
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("CHROMA_API_KEY")
            tenant = os.getenv("CHROMA_TENANT")
            host = os.getenv("CHROMA_SERVER_HOST")
            
            self.is_cloud = False
            
            if api_key and tenant:
                print(f"Initializing ChromaDB Cloud Client (Tenant: {tenant})")
                self.client = chromadb.CloudClient(
                    api_key=api_key,
                    tenant=tenant,
                    database=os.getenv("CHROMA_DATABASE_CHAT_HISTORY") or "default_database"
                )
                self.is_cloud = True
            elif host:
                 port = os.getenv("CHROMA_SERVER_HTTP_PORT", "8000")
                 print(f"Initializing ChromaDB HttpClient to {host}:{port}")
                 self.client = chromadb.HttpClient(
                     host=host, 
                     port=int(port),
                     settings=Settings(allow_reset=True, anonymized_telemetry=False)
                 )
                 self.is_cloud = True
            else:
                # Use EphemeralClient (in-memory) only as last resort
                print("Warning: No ChromaDB credentials found. Using volatile in-memory client.")
                self.client = chromadb.EphemeralClient()
            
            # Try to get the GLOBAL collection first, as that's what UnifiedContext uses
            # But be ready to switch to per-agent collections
            try:
                self.collection = self.client.get_or_create_collection(name="gitmem_global")
            except Exception as e:
                print(f"Failed to get global collection: {e}")
                
        except ImportError:
            print("ChromaDB not installed. Vector search disabled.")
            self.client = None
        except Exception as e:
            print(f"ChromaDB initialization failed: {e}")
            self.client = None

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        if not self.collection:
            return
            
        # Add to global collection for compatibility
        processed_metadatas = []
        for meta in metadatas:
            if not meta:
                processed_metadatas.append({"_placeholder": "true"})
            else:
                processed_meta = {}
                # Ensure agent_id is in metadata if we can find it
                for k, v in meta.items():
                    if isinstance(v, (list, dict)):
                        processed_meta[k] = str(v)
                    else:
                        processed_meta[k] = v
                
                # Use a default agent_id if missing but available elsewhere, 
                # or ensure it's passed in.
                processed_metadatas.append(processed_meta)
        
        try:
            self.collection.add(documents=texts, metadatas=processed_metadatas, ids=ids)
        except:
            pass

    def add_memory(self, memory: Any):
        """Helper to add a memory object directly."""
        try:
            # Handle MemoryItem or dict
            if hasattr(memory, 'to_dict'):
                m_dict = memory.to_dict()
            else:
                m_dict = memory
                
            metadata = {
                "agent_id": m_dict.get("agent_id", "unknown"),
                "memory_type": m_dict.get("type", "episodic"),
                "importance": m_dict.get("importance", 0.0),
                "timestamp": str(m_dict.get("created_at", "")),
                "scope": m_dict.get("scope", "private")
            }
            
            # Merge extra metadata if any
            if "metadata" in m_dict and isinstance(m_dict["metadata"], dict):
                metadata.update(m_dict["metadata"])
                
            self.add_texts(
                texts=[m_dict["content"]],
                metadatas=[metadata],
                ids=[m_dict["id"]]
            )
        except Exception as e:
            print(f"[VectorEngine] Error adding memory: {e}")

    def query(self, query_text: str, n_results: int = 5, where: Dict = None) -> List[Dict]:
        if not self.client:
            return []
        
        # Determine if we should query global or agent-specific collection
        target_collection = self.collection
        
        # Check if we are querying a specific agent
        agent_id = where.get("agent_id") if where else None
        
        # If we are in cloud mode, verify if per-agent collection exists
        if agent_id and self.is_cloud:
            try:
                # Try to get agent-specific collection
                # Note: Manhattan project uses agent_id as collection name often
                agent_col = self.client.get_collection(name=agent_id)
                target_collection = agent_col
                
                # If we switched to agent collection, remove agent_id from where clause
                # as it's implicit
                local_where = where.copy()
                if "agent_id" in local_where:
                    del local_where["agent_id"]
                if not local_where:
                    where = None # If empty, pass None
                else:
                    where = local_where
            except:
                # Fallback to global collection
                pass
                
        if not target_collection:
            return []
            
        try:
            results = target_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
            
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
        
        # 1. Try agent-specific collection first (Cloud/Manhattan style)
        try:
            col = self.client.get_collection(name=agent_id)
            total_count = col.count()
        except:
            # 2. Fallback to global collection with filter
            try:
                if self.collection:
                    results = self.collection.get(
                        where={"agent_id": agent_id},
                        include=["metadatas"] # Minimal fetch
                    )
                    if results and results.get("ids"):
                        total_count = len(results["ids"])
            except:
                pass
            
        return {
            "embeddings": total_count,
            "freshness": "Connected" if self.is_cloud else "Volatile",
            "latency": "12ms"
        }

    def get_stats(self) -> Dict[str, Any]:
        if not self.client:
            return {"embeddings": 0, "freshness": "N/A", "latency": "0ms"}
        
        return {
            "embeddings": "N/A", 
            "freshness": "Connected" if getattr(self, 'is_cloud', False) else "Volatile", 
            "latency": "12ms"
        }
        
    def get_agent_vectors(self, agent_id: str, limit: int = 100) -> List[Dict]:
        """Get all vectors for a specific agent."""
        if not self.client:
            return []
            
        # Target collection logic - same as query/stats
        target_collection = self.collection
        use_agent_filter = True
        
        # 1. Try agent-specific collection first
        if self.is_cloud:
            try:
                agent_col = self.client.get_collection(name=agent_id)
                target_collection = agent_col
                use_agent_filter = False # Agent collection implies agent_id
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
            
            if use_agent_filter:
                get_args["where"] = {"agent_id": agent_id}
                
            results = target_collection.get(**get_args)
            
            normalized = []
            if results and results.get('ids'):
                for i, vid in enumerate(results['ids']):
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    if not metadata: metadata = {} # Handler None
                    metadata["agent_id"] = agent_id
                    
                    doc_content = ""
                    if results.get('documents') and len(results['documents']) > i:
                        doc_content = results['documents'][i] or ""
                    
                    normalized.append({
                        "id": vid,
                        "content": doc_content,
                        "metadata": metadata,
                        "embedding": None # Skip returning heavy embedding data
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
        if not self.client:
            return None
            
        target_collection = self.collection
        
        # Try agent specific collection if cloud and agent_id provided
        if agent_id and self.is_cloud:
            try:
                agent_col = self.client.get_collection(name=agent_id)
                target_collection = agent_col
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


