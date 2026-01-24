"""
Unified Context Service for GitMem

This service integrates multiple data sources to provide a unified context:
- Local filesystem (gitmem_data/)
- Supabase (cloud persistence)
- ChromaDB (vector embeddings)
- MCP Server (Model Context Protocol)
- Manhattan API (agent management)

All sources are queried and merged to provide a complete context view per agent.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class UnifiedContextService:
    """
    Service that aggregates context from multiple sources for an agent.
    """
    
    def __init__(self, memory_store, vector_engine, supabase_connector=None):
        self.store = memory_store
        self.vector = vector_engine
        self.db = supabase_connector
        
        # MCP client (lazy loaded)
        self._mcp_client = None
        
        # Manhattan API client (lazy loaded)  
        self._manhattan_client = None
        
        # Cache for source availability
        self._sources_cache = {}
        self._sources_cache_time = None
    
    def get_available_sources(self) -> Dict[str, bool]:
        """Check which data sources are available."""
        # Use cache if fresh (< 30 seconds)
        if self._sources_cache_time and (datetime.now() - self._sources_cache_time).seconds < 30:
            return self._sources_cache
        
        sources = {
            "local": True,  # Always available
            "supabase": False,
            "chromadb": False,
            "mcp": False,
            "manhattan": False
        }
        
        # Check Supabase
        if self.db and self.db.client and not getattr(self.db, '_disabled', False):
            sources["supabase"] = True
        
        # Check ChromaDB
        if self.vector and self.vector.collection:
            sources["chromadb"] = True
            sources["chromadb_count"] = self.vector.collection.count() if self.vector.collection else 0
        
        # Check MCP
        try:
            from api.mcp_memory_server import _agents_service
            sources["mcp"] = True
        except:
            pass
        
        # Check Manhattan API
        try:
            from api.api_manhattan import service as manhattan_service
            sources["manhattan"] = manhattan_service is not None
        except:
            pass
        
        # Local file count
        sources["local_count"] = self._count_local_files()
        
        self._sources_cache = sources
        self._sources_cache_time = datetime.now()
        
        return sources
    
    def _count_local_files(self) -> int:
        """Count files in local storage."""
        count = 0
        memory_path = os.path.join(self.store.root_path, "memory")
        if os.path.exists(memory_path):
            for mtype in os.listdir(memory_path):
                type_path = os.path.join(memory_path, mtype)
                if os.path.isdir(type_path):
                    count += len(os.listdir(type_path))
        return count
    
    def get_all_agents(self, user_id: str = None) -> List[Dict[str, Any]]:
        """
        Get all agents from all sources.
        Merges agents from:
        - Local refs/agents/
        - Supabase gitmem_commits (distinct agent_ids)
        - MCP mcp_agents table
        - Manhattan api_agents table
        
        If user_id is provided, filters agents by that user where applicable.
        """
        agents_map = {}  # Dedupe by agent_id
        
        # 1. Local agents from refs
        # Local agents are not user-scoped yet (shared environment), so we include them if no user_id or if we want to show local ones always?
        # For now, we include them always as "local workspace" agents.
        local_agents = self._get_local_agents()
        for a in local_agents:
            agents_map[a["id"]] = a
        
        # 2. Supabase agents (from distinct agent_ids in memories/commits)
        # If user_id is provided, we rely on _get_manhattan_agents to get the authoritative list of user's agents.
        # We skip this heuristic scan if we are looking for specific user's agents to avoid clutter.
        if not user_id:
            supabase_agents = self._get_supabase_agents()
            for a in supabase_agents:
                if a["id"] not in agents_map:
                    agents_map[a["id"]] = a
                else:
                    # Merge info
                    agents_map[a["id"]]["source"] = "multi"
        
        # 3. MCP agents
        mcp_agents = self._get_mcp_agents(user_id=user_id)
        for a in mcp_agents:
            if a["id"] not in agents_map:
                agents_map[a["id"]] = a
            else:
                agents_map[a["id"]]["source"] = "multi"
        
        # 4. Manhattan API agents
        manhattan_agents = self._get_manhattan_agents(user_id=user_id)
        for a in manhattan_agents:
            if a["id"] not in agents_map:
                agents_map[a["id"]] = a
            else:
                agents_map[a["id"]]["source"] = "multi"
        
        # Convert to list and sort by activity
        agents = list(agents_map.values())
        agents.sort(key=lambda x: x.get("last_active_ts", 0), reverse=True)
        
        return agents
    
    def _get_local_agents(self) -> List[Dict]:
        """Get agents from local refs."""
        agents = []
        refs_path = os.path.join(self.store.root_path, "refs", "agents")
        
        if os.path.exists(refs_path):
            for agent_id in os.listdir(refs_path):
                # Count memories for this agent
                memory_count = 0
                commit_count = 0
                
                for mtype in ["episodic", "semantic", "procedural"]:
                    mpath = os.path.join(self.store.root_path, "memory", mtype)
                    if os.path.exists(mpath):
                        memory_count += len([f for f in os.listdir(mpath) if f.startswith(agent_id + "_")])
                
                # Count commits
                commits_path = os.path.join(self.store.root_path, "commits")
                if os.path.exists(commits_path):
                    for fname in os.listdir(commits_path):
                        try:
                            with open(os.path.join(commits_path, fname)) as f:
                                c = json.load(f)
                                if c.get("agent_id") == agent_id:
                                    commit_count += 1
                        except:
                            pass
                
                agents.append({
                    "id": agent_id,
                    "name": agent_id,
                    "description": f"Local agent repository",
                    "status": "offline",
                    "source": "local",
                    "memory_count": memory_count,
                    "commit_count": commit_count,
                    "last_active": "Unknown",
                    "last_active_ts": 0,
                    "color": self._generate_color(agent_id)
                })
        
        return agents
    
    def _get_supabase_agents(self) -> List[Dict]:
        """Get distinct agents from Supabase."""
        if not self.db or not self.db.client or getattr(self.db, '_disabled', False):
            return []
        
        agents = []
        try:
            # Get distinct agent_ids from memories
            res = self.db.client.table("gitmem_memories").select("agent_id").execute()
            agent_ids = set(r["agent_id"] for r in res.data if r.get("agent_id"))
            
            for aid in agent_ids:
                # Count memories
                count_res = self.db.client.table("gitmem_memories").select("*", count="exact").eq("agent_id", aid).limit(1).execute()
                
                agents.append({
                    "id": aid,
                    "name": aid,
                    "description": "Cloud-synced agent",
                    "status": "offline",
                    "source": "supabase",
                    "memory_count": count_res.count or 0,
                    "commit_count": 0,
                    "last_active": "Cloud",
                    "last_active_ts": 0,
                    "color": self._generate_color(aid)
                })
        except Exception as e:
            print(f"[UnifiedContext] Supabase query failed: {e}")
        
        return agents
    
    def _get_mcp_agents(self, user_id: str = None) -> List[Dict]:
        """Get agents from MCP server."""
        agents = []
        try:
            from api.mcp_memory_server import _agents_service, _default_user_id
            
            target_user_id = user_id if user_id else _default_user_id
            mcp_agents = _agents_service.list_agents(target_user_id)
            
            for a in mcp_agents:
                agents.append({
                    "id": a.get("agent_id", a.get("id")),
                    "name": a.get("name", a.get("agent_id")),
                    "description": a.get("description", "MCP Agent"),
                    "status": a.get("status", "offline"),
                    "source": "mcp",
                    "memory_count": a.get("memory_count", 0),
                    "commit_count": 0,
                    "last_active": a.get("updated_at", "Unknown"),
                    "last_active_ts": 0,
                    "color": self._generate_color(a.get("agent_id", ""))
                })
        except Exception as e:
            print(f"[UnifiedContext] MCP query failed: {e}")
        
        return agents
    
    def _get_manhattan_agents(self, user_id: str = None) -> List[Dict]:
        """Get agents from Manhattan API."""
        agents = []
        try:
            from api.api_manhattan import service as manhattan_service
            # Fetch all agents from Manhattan API (from api_agents table in Supabase)
            # This will show agents created via MCP or API in the GitMem UI
            
            if user_id:
                manhattan_agents = manhattan_service.list_agents_for_user(user_id=user_id, status="active")
            else:
                manhattan_agents = manhattan_service.list_all_agents(status="active", limit=100)
            
            for a in manhattan_agents:
                agent_id = a.get("agent_id", a.get("id"))
                
                # Get REAL memory count from Supabase
                memory_count = 0
                commit_count = 0
                
                if self.db and self.db.client and not getattr(self.db, '_disabled', False):
                    try:
                        # Count memories from gitmem_memories table
                        mem_res = self.db.client.table("gitmem_memories")\
                            .select("*", count="exact")\
                            .eq("agent_id", agent_id)\
                            .limit(1)\
                            .execute()
                        memory_count = mem_res.count or 0
                        
                        # Count commits from gitmem_commits table
                        commit_res = self.db.client.table("gitmem_commits")\
                            .select("*", count="exact")\
                            .eq("agent_id", agent_id)\
                            .limit(1)\
                            .execute()
                        commit_count = commit_res.count or 0
                    except:
                        pass
                
                agents.append({
                    "id": agent_id,
                    "name": a.get("agent_name", a.get("name")),
                    "description": a.get("description", "Manhattan Agent"),
                    "status": a.get("status", "offline"),
                    "source": "manhattan",
                    "memory_count": memory_count,
                    "commit_count": commit_count,
                    "last_active": a.get("updated_at", "Unknown"),
                    "last_active_ts": 0,
                    "color": self._generate_color(agent_id)
                })
        except Exception as e:
            # Manhattan API may not be configured or Supabase may be down
            print(f"[UnifiedContext] Manhattan API query failed: {e}")
        
        return agents
    
    def get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """
        Get complete context for an agent from all sources.
        Fetches REAL data from Supabase, ChromaDB, MCP, and local storage.
        """
        context = {
            "episodic": [],
            "semantic": [],
            "procedural": [],
            "working": [],
            "mcp": [],
            "supabase": [],
            "vectors": []
        }
        
        # Track IDs to avoid duplicates
        seen_ids = set()
        
        # 1. Fetch from Supabase FIRST (primary source of truth)
        if self.db and self.db.client and not getattr(self.db, '_disabled', False):
            try:
                # Query gitmem_memories table for this agent
                res = self.db.client.table("gitmem_memories")\
                    .select("*")\
                    .eq("agent_id", agent_id)\
                    .order("created_at", desc=True)\
                    .limit(100)\
                    .execute()
                
                for m in res.data:
                    mem_id = m.get("id", str(uuid.uuid4()))
                    if mem_id in seen_ids:
                        continue
                    seen_ids.add(mem_id)
                    
                    mem_type = m.get("type", "episodic").lower()
                    memory_obj = {
                        "id": mem_id,
                        "content": m.get("content", m.get("lossless_restatement", "")),
                        "type": mem_type,
                        "importance": m.get("importance", 0.5),
                        "created_at": m.get("created_at", datetime.now().isoformat()),
                        "metadata": m.get("metadata", {}),
                        "keywords": m.get("keywords", []),
                        "source": "supabase"
                    }
                    
                    # Add to appropriate category
                    if mem_type in ["episodic", "semantic", "procedural", "working"]:
                        context[mem_type].append(memory_obj)
                    else:
                        # Default to episodic if type is unknown
                        context["episodic"].append(memory_obj)
                        
            except Exception as e:
                print(f"[UnifiedContext] Supabase gitmem_memories query failed: {e}")
        
        # 2. Fetch from ChromaDB (vector store)
        if self.vector and self.vector.collection:
            try:
                # Use updated get_agent_vectors to fetch data efficiently
                vectors = self.vector.get_agent_vectors(agent_id, limit=100)
                
                # Categorize vectors into bins based on metadata
                categorized = self.vector.categorize_vectors(vectors)
                
                # Merge into main context, respecting seen_ids check
                for bin_name, items in categorized.items():
                    # Handle the bins: episodic, semantic, procedural, working, vectors
                    target_list = context.get(bin_name)
                    if target_list is None: continue # Should not happen based on init
                    
                    for item in items:
                        # Skip if already added (e.g. from Supabase)
                        if item["id"] in seen_ids:
                            continue
                        
                        seen_ids.add(item["id"])
                        target_list.append(item)
                        
            except Exception as e:
                print(f"[UnifiedContext] ChromaDB query failed: {e}")
        
        # 3. Fetch from MCP memory system
        try:
            # Try to import and use MCP memory system
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api'))
            
            from api_manhattan import service as manhattan_service
            
            # Query Manhattan API for memories
            import requests
            API_URL = os.getenv("MANHATTAN_API_URL", "http://127.0.0.1:1078")
            API_KEY = os.getenv("MANHATTAN_API_KEY", "sk-tg5T-vIyYnuprwVPcgoHGfX37HBsfPwAvHkV3WFyhkE")
            
            response = requests.post(
                f"{API_URL}/read_memory",
                json={"agent_id": agent_id, "query": "", "top_k": 50},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and data.get("memories"):
                    for m in data["memories"]:
                        mem_id = m.get("id", str(uuid.uuid4()))
                        if mem_id in seen_ids:
                            continue
                        seen_ids.add(mem_id)
                        
                        mem_obj = {
                            "id": mem_id,
                            "content": m.get("content", m.get("lossless_restatement", "")),
                            "type": m.get("memory_type", "episodic"),
                            "importance": m.get("importance", 0.5),
                            "created_at": m.get("timestamp", m.get("created_at", "")),
                            "metadata": m.get("metadata", {}),
                            "source": "mcp"
                        }
                        
                        # Add to MCP source list
                        context["mcp"].append(mem_obj)
                        
                        # ALso add to specific category bin for folder visibility
                        mtype = str(mem_obj["type"]).lower()
                        target_bin = None
                        if "episodic" in mtype or "persistent" in mtype: target_bin = "episodic"
                        elif "semantic" in mtype: target_bin = "semantic"
                        elif "procedural" in mtype: target_bin = "procedural"
                        elif "working" in mtype: target_bin = "working"
                        
                        if target_bin:
                            # We create a copy for the bin to avoid reference issues if lists are mutated differently
                            bin_obj = mem_obj.copy()
                            context[target_bin].append(bin_obj)
        except Exception as e:
            print(f"[UnifiedContext] MCP query failed: {e}")
        
        # 4. Local filesystem memories (fallback)
        try:
            for mtype in ["episodic", "semantic", "procedural", "working"]:
                memories = self.store.list_memories(agent_id, mtype, limit=50)
                for m in memories:
                    mem_id = m.id if hasattr(m, 'id') else str(uuid.uuid4())
                    if mem_id in seen_ids:
                        continue
                    seen_ids.add(mem_id)
                    
                    context[mtype].append({
                        "id": mem_id,
                        "content": m.content if hasattr(m, 'content') else str(m),
                        "type": mtype,
                        "importance": m.importance if hasattr(m, 'importance') else 0.5,
                        "created_at": m.created_at.isoformat() if hasattr(m, 'created_at') and hasattr(m.created_at, 'isoformat') else str(m.created_at) if hasattr(m, 'created_at') else datetime.now().isoformat(),
                        "source": "local"
                    })
        except Exception as e:
            print(f"[UnifiedContext] Local filesystem query failed: {e}")
        
        return context
    
    def get_recent_context(self, agent_id: str, limit: int = 20) -> List[Dict]:
        """Get recent context items from all sources, sorted by time."""
        context = self.get_agent_context(agent_id)
        
        # Flatten all context
        all_items = []
        for source, items in context.items():
            all_items.extend(items)
        
        # Sort by created_at (newest first)
        all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return all_items[:limit]
    
    def sync_agent_sources(self, agent_id: str) -> Dict[str, int]:
        """
        Sync an agent's context across all sources.
        Pulls Cloud memories to Local Storage (hybrid sync).
        """
        synced = {"cloud_to_local": 0, "local_to_cloud": 0}
        
        # 1. Cloud to Local (Supabase -> JSON files)
        if self.db and self.db.client and not getattr(self.db, '_disabled', False):
            try:
                # Fetch all memories for this agent (limit 1000)
                cloud_mems = self.db.get_memories(agent_id, None, limit=1000)
                count = 0
                for mem_data in cloud_mems:
                    try:
                        # Ensure ID is present
                        if not mem_data.get("id"): continue
                        
                        # Convert to MemoryItem (Pydantic will handle types)
                        mem = MemoryItem(**mem_data)
                        
                        # Save locally
                        self.store.save_to_local_file(mem)
                        count += 1
                    except Exception as e:
                        # print(f"Failed to sync memory item {mem_data.get('id')}: {e}")
                        pass
                
                synced["cloud_to_local"] = count
            except Exception as e:
                print(f"Sync error (cloud->local): {e}")
        
        # Refresh cache
        self._sources_cache_time = None
        
        return synced
    
    def _generate_color(self, agent_id: str) -> str:
        """Generate a consistent gradient color based on agent ID."""
        # Simple hash-based color generation
        hash_val = sum(ord(c) for c in agent_id)
        colors = [
            "from-blue-500 to-purple-600",
            "from-green-500 to-teal-600",
            "from-orange-500 to-red-600",
            "from-pink-500 to-rose-600",
            "from-indigo-500 to-blue-600",
            "from-cyan-500 to-blue-600",
            "from-violet-500 to-purple-600",
            "from-amber-500 to-orange-600"
        ]
        return colors[hash_val % len(colors)]
    
    def get_agent_info(self, agent_id: str, user_id: str = None) -> Optional[Dict]:
        """Get detailed info about a specific agent."""
        # Check all sources
        agents = self.get_all_agents(user_id=user_id)
        for a in agents:
            if a["id"] == agent_id:
                return a
        
        # Create default if not found
        return {
            "id": agent_id,
            "name": agent_id,
            "description": "Agent memory repository",
            "status": "offline",
            "source": "new",
            "memory_count": 0,
            "commit_count": 0,
            "color": self._generate_color(agent_id)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated stats across all sources."""
        sources = self.get_available_sources()
        agents = self.get_all_agents()
        
        # Count active agents (with recent activity)
        active = sum(1 for a in agents if a.get("status") == "online")
        
        return {
            "active_agents": active,
            "total_agents": len(agents),
            "total_memories": sum(a.get("memory_count", 0) for a in agents),
            "total_commits": sum(a.get("commit_count", 0) for a in agents),
            "sources": sources
        }
    
    def get_folder_structure(self, agent_id: str) -> Dict[str, Any]:
        """
        Get complete folder structure with item counts for an agent.
        Aggregates data from Supabase and ChromaDB using parallel queries.
        """
        structure = {
            "agent_id": agent_id,
            "context": {
                "episodic": {"count": 0, "label": "Events & Interactions", "icon": "clock", "color": "blue"},
                "semantic": {"count": 0, "label": "Facts & Knowledge", "icon": "book-open", "color": "purple"},
                "procedural": {"count": 0, "label": "Skills & Procedures", "icon": "cog", "color": "green"},
                "working": {"count": 0, "label": "Current Session State", "icon": "brain", "color": "orange"}
            },
            "documents": {
                "uploads": {"count": 0, "label": "User Uploaded Files", "icon": "upload", "color": "blue"},
                "attachments": {"count": 0, "label": "Conversation Files", "icon": "paperclip", "color": "green"},
                "references": {"count": 0, "label": "Reference Documents", "icon": "book", "color": "purple"}
            },
            "checkpoints": {
                "snapshots": {"count": 0, "label": "Full State Backups", "icon": "camera", "color": "blue"},
                "sessions": {"count": 0, "label": "Session Checkpoints", "icon": "clock", "color": "green"},
                "recovery": {"count": 0, "label": "Recovery Points", "icon": "shield", "color": "yellow"}
            },
            "sources": {
                "api": {"count": 0, "label": "API Call Logs", "icon": "globe", "color": "blue"},
                "mcp": {"count": 0, "label": "MCP Server Inputs", "icon": "server", "color": "purple"},
                "webhooks": {"count": 0, "label": "Webhook Events", "icon": "webhook", "color": "orange"}
            },
            "logs": {
                "access": {"count": 0, "label": "Read Operations", "icon": "eye", "color": "blue"},
                "mutations": {"count": 0, "label": "Write Operations", "icon": "edit", "color": "green"},
                "errors": {"count": 0, "label": "Failed Operations", "icon": "alert-circle", "color": "red"}
            },
            "external": {
                "mcp": {"connected": False, "count": 0, "label": "MCP Server"},
                "chromadb": {"connected": False, "count": 0, "label": "ChromaDB Vectors"}
            }
        }
        
        # Parallel execution helper
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_count(table, **kwargs):
            try:
                query = self.db.client.table(table).select("*", count="exact")
                for k, v in kwargs.items():
                    query = query.eq(k, v)
                res = query.limit(1).execute()
                return res.count or 0
            except:
                return 0

        if self.db and self.db.client:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {}
                
                # Context memories
                for mem_type in ["episodic", "semantic", "procedural", "working"]:
                    futures[executor.submit(fetch_count, "gitmem_memories", agent_id=agent_id, type=mem_type)] = ("context", mem_type)
                
                # Documents
                for folder in ["uploads", "attachments", "references"]:
                    futures[executor.submit(fetch_count, "gitmem_documents", agent_id=agent_id, folder=folder)] = ("documents", folder)
                
                # Checkpoints
                for cp_type in ["snapshot", "session", "recovery"]:
                    futures[executor.submit(fetch_count, "gitmem_checkpoints", agent_id=agent_id, checkpoint_type=cp_type)] = ("checkpoints", cp_type + ("s" if cp_type != "recovery" else ""))
                
                # Misc logs (clubbed separately in map)
                futures[executor.submit(fetch_count, "gitmem_api_logs", agent_id=agent_id)] = ("sources", "api")
                futures[executor.submit(fetch_count, "gitmem_mcp_inputs", agent_id=agent_id)] = ("sources", "mcp")
                futures[executor.submit(fetch_count, "gitmem_webhooks", agent_id=agent_id)] = ("sources", "webhooks")
                
                # Activity logs
                for log_type in ["access", "mutation", "error"]:
                    futures[executor.submit(fetch_count, "gitmem_activity_logs", agent_id=agent_id, log_type=log_type)] = ("logs", log_type + ("s" if log_type != "access" else ""))

                # Collect results
                for future in as_completed(futures):
                    category, key = futures[future]
                    try:
                        count = future.result()
                        structure[category][key]["count"] = count
                    except Exception as e:
                        print(f"Error fetching count for {category}.{key}: {e}")

        # Fetch ChromaDB counts (keep synchronous as it might be local http or fast)
        if self.vector and self.vector.client:
            try:
                # Try agent-specific collection first
                try:
                    agent_col = self.vector.client.get_collection(name=agent_id)
                    structure["external"]["chromadb"]["count"] = agent_col.count()
                    structure["external"]["chromadb"]["connected"] = True
                except:
                    # Fall back to global collection with filter
                    if self.vector.collection:
                        try:
                            results = self.vector.collection.get(
                                where={"agent_id": agent_id},
                                include=["metadatas"]
                            )
                            structure["external"]["chromadb"]["count"] = len(results.get("ids", []))
                            structure["external"]["chromadb"]["connected"] = True
                        except:
                            pass
            except Exception as e:
                print(f"[UnifiedContext] Error fetching ChromaDB counts: {e}")
        
        # Check MCP connection
        try:
            from api.mcp_memory_server import _agents_service
            if _agents_service:
                structure["external"]["mcp"]["connected"] = True
                structure["external"]["mcp"]["count"] = structure["sources"]["mcp"]["count"]
        except:
            pass
        
        # Fallback: If all context counts are 0, try to get counts from agent context
        total_context_count = sum(structure["context"][k]["count"] for k in structure["context"])
        if total_context_count == 0:
            try:
                context = self.get_agent_context(agent_id)
                for mem_type in ["episodic", "semantic", "procedural", "working"]:
                    if mem_type in context:
                        structure["context"][mem_type]["count"] = len(context[mem_type])
            except Exception as e:
                print(f"[UnifiedContext] Fallback context count failed: {e}")
        
        return structure

