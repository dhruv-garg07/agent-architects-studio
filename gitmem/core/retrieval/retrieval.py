"""
GitMem v2.0 — Retrieval Orchestrator (THE MOAT)

The intelligence core of GitMem. Combines multiple retrieval strategies
to find the perfect context for an agent's prompt.

Pipeline:
1. Retrieval (Semantic + Recency + Importance + Episodic + Graph)
2. Deduplication
3. Reranking (Multi-signal)
4. Token Packing
5. (Optional) Summarization of overflow
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from gitmem.core.retrieval.ranker import Ranker
from gitmem.core.retrieval.token_packer import TokenPacker
from gitmem.core.retrieval.summarizer import Summarizer
from gitmem.core.retrieval.embedder import Embedder


class RetrievalOrchestrator:
    """Combines all retrieval strategies to build the optimal context window."""
    
    def __init__(self, supabase_client, chroma_adapter):
        self.client = supabase_client
        self.vector_store = chroma_adapter
        
        self.ranker = Ranker()
        self.packer = TokenPacker(max_tokens=4000)
        self.summarizer = Summarizer()
        self.embedder = Embedder()
        
        # New: LLM Client for dynamic query analysis
        from SimpleMem.utils.llm_client import LLMClient
        self.llm_client = LLMClient()
        
        self._table = "gitmem_memories"

    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Use LLM to analyze query intent and extract structured information
        """
        prompt = f"""Analyze the following query and extract key information for memory retrieval:

Query: {query}

Please extract:
1. keywords: List of core keywords (names, places, technical terms)
2. topic_category: Optional string representing the broad topic.
3. time_expression: Time expression (if any)
4. metadata_filters: A dictionary of key-value pairs matching specific constraints in the user's query. You may extract ANY of the following fields if present: `timestamp`, `context_location`, `participants`, `event_type`, `outcome`, `sentiment`, `domain`, `related_entities`, `provenance`, `trigger_condition`, `steps`, `prerequisites`, `tools_required`, `decision_context`, `options_considered`, `chosen_option`, `state_key`, `state_value`, `scope`.

Return in JSON format:
```json
{{
  "keywords": ["keyword1", "keyword2", ...],
  "topic_category": "topic or null",
  "time_expression": "time expression or null",
  "metadata_filters": {{
    "participants": ["name1", "name2"],
    "event_type": "meeting"
  }}
}}
```

Return ONLY JSON, no other content.
"""
        messages = [
            {"role": "system", "content": "You are a query analysis assistant. You must output valid JSON format."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.llm_client.chat_completion(messages, temperature=0.1)
            analysis = self.llm_client.extract_json(response)
            return analysis
        except Exception as e:
            print(f"Query analysis failed: {e}")
            return {
                "keywords": [query],
                "topic_category": None,
                "time_expression": None,
                "metadata_filters": {}
            }

    def _semantic_search(self, query: str, agent_id: str, limit: int = 10, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """1. Vector search via ChromaDB."""
        if not self.vector_store:
            return []
            
        try:
            # Format metadata filters for ChromaDB
            where_clause = None
            if metadata_filters:
                valid_filters = []
                for k, v in metadata_filters.items():
                    if isinstance(v, (str, int, float, bool)):
                        valid_filters.append({k: v})
                    elif isinstance(v, list) and v and all(isinstance(x, (str, int, float, bool)) for x in v):
                        valid_filters.append({k: {"$in": v}})
                
                if len(valid_filters) == 1:
                    where_clause = valid_filters[0]
                elif len(valid_filters) > 1:
                    where_clause = {"$and": valid_filters}
            results = self.vector_store.query(
                query_text=query,
                collection_name=agent_id,
                n_results=limit,
                where=where_clause
            )
            
            # Fallback: if metadata filters produced zero results, retry without them.
            # LLM-generated filters may not match stored metadata schema.
            if not results and where_clause:
                results = self.vector_store.query(
                    query_text=query,
                    collection_name=agent_id,
                    n_results=limit,
                    where=None
                )
            
            # VectorEngine.query returns normalized List[Dict]
            formatted = []
            for res in results:
                formatted.append({
                    "id": res["id"],
                    "content": res["content"],
                    "semantic_score": 1.0 - (res.get("distance", 0) / 2.0) # Heuristic
                })
                    
            # Fetch full metadata from Supabase for these IDs
            if formatted and self.client:
                ids = [f["id"] for f in formatted]
                res = self.client.table(self._table).select("*").in_("id", ids).execute()
                db_data = {r["id"]: r for r in res.data or []}
                
                # Merge
                for f in formatted:
                    if f["id"] in db_data:
                        f.update(db_data[f["id"]])
                        
            return formatted
        except Exception as e:
            print(f"[Retrieval] Semantic search failed: {e}")
            return []

    def _recency_search(self, repo_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """2. Get most recent episodic memories."""
        if not self.client:
            return []
        try:
            # Try agent_id first (primary key used by most of the codebase),
            # then fall back to repo_id (legacy alias set by supabase_connector).
            res = self.client.table(self._table).select("*") \
                .or_(f"agent_id.eq.{repo_id},repo_id.eq.{repo_id}") \
                .order("created_at", desc=True) \
                .limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[Retrieval] Recency search failed: {e}")
            return []

    def _importance_search(self, repo_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """3. Get core principles/rules (high importance semantic/procedural)."""
        if not self.client:
            return []
        try:
            res = self.client.table(self._table).select("*") \
                .or_(f"agent_id.eq.{repo_id},repo_id.eq.{repo_id}") \
                .gte("importance", 0.7) \
                .order("importance", desc=True) \
                .limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[Retrieval] Importance search failed: {e}")
            return []

    def _graph_traversal(self, query: str, repo_id: str) -> List[Dict[str, Any]]:
        """4. Find linked concepts via graph. (Stub for future)"""
        return []

    def retrieve(self, query: str, repo_id: str, agent_id: str, max_tokens: int = 4000) -> Dict[str, Any]:
        """
        Main retrieval pipeline execution.
        """
        self.packer.max_tokens = max_tokens
        
        # 0. Analyze query with LLM to extract dynamic filters
        query_analysis = self._analyze_query(query)
        metadata_filters = query_analysis.get("metadata_filters", {})
        topic_category = query_analysis.get("topic_category")
        if topic_category:
            metadata_filters["topic"] = topic_category
            
        # 1. Gather candidates from all strategies
        semantic_cands = self._semantic_search(query, agent_id, limit=10, metadata_filters=metadata_filters)
        print(f"[DEBUG] semantic_cands: {semantic_cands}")
        recency_cands = self._recency_search(repo_id, limit=5)
        import_cands = self._importance_search(repo_id, limit=5)
        graph_cands = self._graph_traversal(query, repo_id)
        
        # 2. Deduplicate
        seen_ids = set()
        unique_cands = []
        
        for cand in (semantic_cands + recency_cands + import_cands + graph_cands):
            cid = cand.get("id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                unique_cands.append(cand)
                
        # 3. Rerank
        ranked = self.ranker.rerank(unique_cands)
        
        # 4. Pack into token budget
        packed, tokens_used = self.packer.pack(ranked)
        
        # 5. Identify leftovers (for optional summarization)
        packed_ids = {p["id"] for p in packed}
        leftovers = [r for r in ranked if r["id"] not in packed_ids]
        
        # Construct context string
        context_str = "\n\n".join([f"[{p.get('type', 'memory')} | {p.get('created_at', '')[:10]}]: {p.get('content', '')}" for p in packed])
        
        if leftovers:
            summary = self.summarizer.summarize(leftovers)
            if summary:
                context_str += f"\n\n[Additional Context Summary]:\n{summary}"
                
        return {
            "context_string": context_str,
            "memories_used": len(packed),
            "tokens_used": tokens_used,
            "sources": packed
        }
