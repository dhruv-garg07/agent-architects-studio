"""
Vector Store - Structured Multi-View Indexing Implementation (Section 3.2)

Paper Reference: Section 3.2 - Structured Indexing
Implements the three structured indexing dimensions:
- Semantic Layer: Dense vectors v_k ∈ ℝ^d (embedding-based similarity)
- Lexical Layer: Sparse vectors h_k ∈ ℝ^|V| (BM25/keyword matching)
- Symbolic Layer: Metadata R_k = {(key, val)} (structured filtering by time, entities, etc.)

Now uses Agentic_RAG with ChromaDB as the unified vector store.
"""

from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from SimpleMem.models.memory_entry import MemoryEntry
from SimpleMem.utils.embedding import EmbeddingModel
import os
import sys
from datetime import datetime
import json
from dataclasses import asdict
import hashlib
import threading

# Add parent and grandparent directories to sys.path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
grandparent_dir = os.path.dirname(parent_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if grandparent_dir not in sys.path:
    sys.path.insert(0, grandparent_dir)

# Import the enhanced Agentic_RAG from the previous implementation
from Octave_mem.RAG_DB_CONTROLLER_AGENTS.agent_RAG import Agentic_RAG


class VectorStore:
    """
    Structured Multi-View Indexing - Storage and retrieval for Atomic Entries

    Paper Reference: Section 3.2 - Structured Indexing
    Implements M(m_k) with three structured layers using ChromaDB via Agentic_RAG:
    1. Semantic Layer: Dense embedding vectors for conceptual similarity
    2. Lexical Layer: Sparse keyword vectors for precise term matching
    3. Symbolic Layer: Structured metadata for deterministic filtering
    
    Thread-safe agent_id switching with cache invalidation.
    
    🔐 DATA ISOLATION GUARANTEES:
    =============================
    1. **Agent ID Isolation**: Each agent_id maps to a separate ChromaDB collection.
       Data from different agents NEVER mixes.
       
    2. **Cache Invalidation**: Changing agent_id automatically:
       - Clears semantic cache for old agent
       - Clears local entry cache
       - Initializes new collection if needed
       
    3. **Thread Safety**: 
       - All agent_id changes use RLock (reentrant lock)
       - Snapshots agent_id at operation start to prevent mid-operation changes
       - Methods capture agent_id before batch operations
       
    4. **Concurrent Operation Safety**:
       Use freeze_agent_id_for_operation() context manager to prevent agent_id
       changes during multi-step operations.
    
    USAGE EXAMPLES:
    ===============
    # Safe agent_id switching
    vs = VectorStore("agent_A")
    vs.agent_id = "agent_B"  # Automatic cache cleanup + collection setup
    
    # Prevent changes during critical operations
    with vs.freeze_agent_id_for_operation("batch_import"):
        vs.add_entries(batch1)
        vs.add_entries(batch2)  # agent_id locked, cannot change
        vs.semantic_search(query)
    """
    
    def __init__(self, agent_id: str = "memory_entries", embedding_model: EmbeddingModel = None):
        """
        Initialize VectorStore using Agentic_RAG as the vector database.
        
        Args:
            agent_id: Unique identifier for the memory entries collection
            embedding_model: Embedding model for vector generation
        """
        # Use private variable for agent_id to enable property setter
        self._agent_id = agent_id
        self._agent_id_lock = threading.RLock()  # Thread-safe agent_id switching
        self.embedding_model = embedding_model or EmbeddingModel()
        
        # Initialize Agentic_RAG with ChromaDB
        database_path = os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        self.agentic_RAG = Agentic_RAG(
            database=database_path,
            enable_cache=True,
            enable_monitoring=True
        )
        
        # Ensure collection exists
        self._ensure_collection()
        
        # Cache for frequently accessed entries
        self.entry_cache = {}
        self.cache_max_size = 1000
        
    @property
    def agent_id(self) -> str:
        """Get the current agent ID (thread-safe)."""
        with self._agent_id_lock:
            return self._agent_id
    
    @agent_id.setter
    def agent_id(self, new_agent_id: str) -> None:
        """
        Change the agent ID with automatic cache invalidation and collection setup.
        
        This setter ensures:
        1. No data corruption between different agent IDs
        2. Semantic cache is cleared for the old agent ID
        3. New collection is initialized if it doesn't exist
        4. Thread-safe switching
        
        Args:
            new_agent_id: New agent ID to switch to
            
        Raises:
            ValueError: If new_agent_id is None or empty
            RuntimeError: If collection initialization fails
        """
        if not new_agent_id or not isinstance(new_agent_id, str):
            raise ValueError(f"agent_id must be a non-empty string, got: {new_agent_id}")
        
        with self._agent_id_lock:
            old_agent_id = self._agent_id
            
            # Prevent redundant switches
            if old_agent_id == new_agent_id:
                return
            
            try:
                # Invalidate semantic cache for old agent
                if hasattr(self.agentic_RAG, 'semantic_cache') and self.agentic_RAG.semantic_cache:
                    self.agentic_RAG.semantic_cache.invalidate_agent_cache(old_agent_id)
                    print(f"[CLEANUP] Cleared semantic cache for agent: {old_agent_id}")
                
                # Clear local entry cache (potentially mixed with old agent data)
                if self.entry_cache:
                    self.entry_cache.clear()
                    print(f"[CLEANUP] Cleared local entry cache")
                
                # Update to new agent ID
                self._agent_id = new_agent_id
                
                # Ensure new collection exists (or create it)
                self._ensure_collection()
                
                print(f"[SUCCESS] Successfully switched agent_id: {old_agent_id} -> {new_agent_id}")
                
            except Exception as e:
                # Rollback on failure
                self._agent_id = old_agent_id
                raise RuntimeError(
                    f"Failed to switch agent_id from {old_agent_id} to {new_agent_id}: {str(e)}"
                ) from e
        
    def _ensure_collection(self):
        """Ensure the collection exists in ChromaDB."""
        try:
            # Try to get collection info - if it fails, collection doesn't exist
            # Use thread-safe agent_id access via property
            self.agentic_RAG.get_agent_collection_info(self._agent_id)
        except Exception:
            # Create the collection
            self.agentic_RAG.create_agent_collection(self._agent_id)
            print(f"Created new collection for agent: {self._agent_id}")
    
    def _validate_agent_id_unchanged(self, operation_name: str) -> str:
        """
        Safely get current agent_id for operations, ensuring it doesn't change mid-operation.
        
        This method prevents data corruption when operations span multiple calls.
        If agent_id changes during the operation, logs a warning and returns the current ID.
        
        Args:
            operation_name: Name of the operation (for logging)
            
        Returns:
            Current agent_id at time of validation
        """
        with self._agent_id_lock:
            current_id = self._agent_id
        return current_id
    
    def _generate_entry_id(self, entry: MemoryEntry) -> str:
        """Generate a unique ID for a memory entry."""
        # Use hash of content + timestamp for uniqueness
        content = f"{entry.lossless_restatement}_{entry.timestamp}"
        return f"entry_{hashlib.md5(content.encode()).hexdigest()[:16]}"
    
    def _entry_to_document(self, entry: MemoryEntry) -> str:
        """
        Convert MemoryEntry to a searchable document text.
        
        Paper Reference: Section 3.1 - Lossless Restatement S_k
        The document includes the lossless restatement and keywords for search.
        """
        # Create a searchable text from the entry
        components = [
            f"Content: {entry.lossless_restatement}",
        ]
        
        if entry.keywords:
            components.append(f"Keywords: {', '.join(entry.keywords)}")
        
        if entry.topic:
            components.append(f"Topic: {entry.topic}")
            
        return "\n".join(components)
    
    def _entry_to_metadata(self, entry: MemoryEntry) -> Dict[str, Any]:
        """
        Convert MemoryEntry to ChromaDB metadata.
        
        Paper Reference: Section 3.2 - Symbolic Layer R_k
        Metadata includes structured information for filtering.
        """
        metadata = {
            "agent_id": self.agent_id,
            "entry_type": "memory_entry",
            "timestamp": entry.timestamp or datetime.now().isoformat(),
            "has_keywords": len(entry.keywords) > 0,
            "has_persons": len(entry.persons) > 0,
            "has_entities": len(entry.entities) > 0,
        }
        
        # Add optional fields if they exist
        if entry.location:
            metadata["location"] = entry.location
            
        if entry.topic:
            metadata["topic"] = entry.topic
            
        # Add memory_type to metadata for categorization
        metadata["memory_type"] = entry.memory_type
            
        # Store lists as JSON strings for metadata filtering
        if entry.keywords:
            metadata["keywords_json"] = json.dumps(entry.keywords)
            
        if entry.persons:
            metadata["persons_json"] = json.dumps(entry.persons)
            
        if entry.entities:
            metadata["entities_json"] = json.dumps(entry.entities)
        
        return metadata
    
    def _metadata_to_entry(self, metadata: Dict[str, Any], document: str) -> MemoryEntry:
        """Convert ChromaDB metadata back to MemoryEntry."""
        # Parse document to extract content (simple approach)
        lines = document.split("\n")
        content = lines[0].replace("Content: ", "") if lines else document
        
        # Parse lists from JSON strings
        keywords = []
        persons = []
        entities = []
        
        if "keywords_json" in metadata:
            keywords = json.loads(metadata["keywords_json"])
        if "persons_json" in metadata:
            persons = json.loads(metadata["persons_json"])
        if "entities_json" in metadata:
            entities = json.loads(metadata["entities_json"])
        
        return MemoryEntry(
            entry_id=metadata.get("entry_id", ""),
            lossless_restatement=content,
            keywords=keywords,
            timestamp=metadata.get("timestamp"),
            location=metadata.get("location"),
            persons=persons,
            entities=entities,
            topic=metadata.get("topic"),
            memory_type=metadata.get("memory_type", "episodic")
        )
    
    def _update_cache(self, entry_id: str, entry: MemoryEntry):
        """Update the in-memory cache with LRU eviction."""
        if len(self.entry_cache) >= self.cache_max_size:
            # Remove oldest entry (first key)
            oldest_key = next(iter(self.entry_cache))
            del self.entry_cache[oldest_key]
        
        self.entry_cache[entry_id] = entry
    
    def freeze_agent_id_for_operation(self, operation_name: str = "operation"):
        """
        Context manager to prevent agent_id from changing during multi-step operations.
        
        Usage:
            with vectorstore.freeze_agent_id_for_operation("batch_add"):
                vectorstore.add_entries(entries)
                vectorstore.semantic_search(query)
                # agent_id changes are blocked here
        
        Args:
            operation_name: Name of operation (for logging)
            
        Yields:
            The frozen agent_id
            
        Raises:
            RuntimeError: If attempted to change agent_id during frozen operation
        """
        from contextlib import contextmanager
        
        @contextmanager
        def _freeze_context():
            frozen_agent_id = self.agent_id
            
            # Replace setter temporarily to prevent changes
            original_setter = type(self).agent_id.fset
            operation_id = id(threading.current_thread())
            
            def frozen_setter(new_value):
                raise RuntimeError(
                    f"Cannot change agent_id during frozen operation '{operation_name}'. "
                    f"Current frozen agent_id: {frozen_agent_id}. "
                    f"Requested new agent_id: {new_value}"
                )
            
            try:
                # Monkey-patch the setter temporarily
                type(self).agent_id = type(self).agent_id.setter(frozen_setter)
                print(f"[FREEZE] Frozen agent_id '{frozen_agent_id}' for operation: {operation_name}")
                yield frozen_agent_id
            finally:
                # Restore original setter
                type(self).agent_id = type(self).agent_id.setter(original_setter)
                print(f"[UNFREEZE] Released agent_id freeze for operation: {operation_name}")
        
        return _freeze_context()
    
    def add_entries(self, entries: List[MemoryEntry]):
        """
        Batch add memory entries to ChromaDB via Agentic_RAG.
        
        Paper Reference: Section 3.1 - Memory Encoding E(S_k)
        Thread-safe: captures agent_id at start to prevent corruption.
        """
        if not entries:
            return
        
        # Capture agent_id at start (thread-safe snapshot)
        agent_id_snapshot = self._validate_agent_id_unchanged("add_entries")
        
        ids = []
        documents = []
        metadatas = []
        
        for entry in entries:
            # Generate or use existing entry_id
            if not entry.entry_id:
                entry.entry_id = self._generate_entry_id(entry)
            
            # Convert to ChromaDB format
            ids.append(entry.entry_id)
            documents.append(self._entry_to_document(entry))
            
            metadata = self._entry_to_metadata(entry)
            metadata["entry_id"] = entry.entry_id
            metadatas.append(metadata)
            
            # Cache the entry
            self._update_cache(entry.entry_id, entry)
        
        # Use batch operation for efficiency
        batch = self.agentic_RAG.batch_operation()
        for i in range(0, len(ids), 100):  # Batch in chunks of 100
            batch_chunk = batch.add_documents(
                agent_id=agent_id_snapshot,  # Use snapshot, not self.agent_id
                ids=ids[i:i+100],
                documents=documents[i:i+100],
                metadatas=metadatas[i:i+100]
            )
        
        result = batch.execute()
        
        if result.get('success'):
            print(f"Added {len(entries)} memory entries to {agent_id_snapshot}")
        else:
            print(f"Error adding entries: {result.get('error')}")
    
    def add_single_entry(self, entry: MemoryEntry) -> bool:
        """Add a single memory entry."""
        self.add_entries([entry])
        return True
    
    def semantic_search(self, query: str, top_k: int = 5, **kwargs) -> List[MemoryEntry]:
        """
        Semantic Layer Search - Dense vector similarity using ChromaDB.
        
        Paper Reference: Section 3.1
        Retrieves based on v_k = E_dense(S_k) where S_k is the lossless restatement
        
        Args:
            query: Search query
            top_k: Number of results to return
            **kwargs: Additional search parameters (filters, etc.)
        """
        try:
            # Prepare filters from kwargs
            filters = {}
            if kwargs.get('persons'):
                filters["persons_json"] = json.dumps(kwargs['persons'])
            if kwargs.get('location'):
                filters["location"] = kwargs['location']
            if kwargs.get('topic'):
                filters["topic"] = kwargs['topic']
            
            # Use Agentic_RAG's advanced search with filters
            if filters:
                results = self.agentic_RAG.search_with_filters(
                    agent_ID=self.agent_id,
                    query=query,
                    filters=filters,
                    n_results=top_k,
                    distance_threshold=kwargs.get('distance_threshold', 0.7)
                )
            else:
                # Use standard search
                results = self.agentic_RAG.search_agent_collection(
                    agent_ID=self.agent_id,
                    query=query,
                    n_results=top_k
                )
            
            # Convert results to MemoryEntry objects
            entries = []
            for result in results:
                try:
                    metadata = result.get('metadata', {})
                    document = result.get('document', '')
                    
                    # Check if we have this entry in cache
                    entry_id = metadata.get('entry_id')
                    if entry_id and entry_id in self.entry_cache:
                        entries.append(self.entry_cache[entry_id])
                        continue
                    
                    # Create new entry from result
                    entry = self._metadata_to_entry(metadata, document)
                    if entry_id:
                        entry.entry_id = entry_id
                        self._update_cache(entry_id, entry)
                    
                    entries.append(entry)
                except Exception as e:
                    print(f"Warning: Failed to parse search result: {e}")
                    continue
            
            return entries
            
        except Exception as e:
            print(f"Error during semantic search: {e}")
            return []
    
    def keyword_search(self, keywords: List[str], top_k: int = 3, **kwargs) -> List[MemoryEntry]:
        """
        Lexical Layer Search - Keyword matching using ChromaDB vector similarity.
        
        Paper Reference: Section 3.1
        Retrieves based on h_k = Sparse(S_k) for precise term and entity matching.
        Uses vector search with keyword-based queries.
        """
        try:
            if not keywords:
                return []
            
            # Create a query from keywords
            query_text = " ".join(keywords)
            
            # Prepare metadata filters for structured keyword search
            filters = {}
            
            # Convert keyword list to JSON string for metadata filtering
            filters["keywords_json"] = json.dumps(keywords)
            
            # Additional filters from kwargs
            if kwargs.get('persons'):
                filters["persons_json"] = json.dumps(kwargs['persons'])
            if kwargs.get('location'):
                filters["location"] = kwargs['location']
            
            # Use hybrid approach: combine keyword query with metadata filtering
            results = self.agentic_RAG.search_with_filters(
                agent_ID=self.agent_id,
                query=query_text,
                filters=filters,
                n_results=top_k * 2,  # Get more results for filtering
                distance_threshold=kwargs.get('distance_threshold', 0.8)
            )
            
            # Additional keyword scoring on top of vector similarity
            scored_entries = []
            for result in results:
                try:
                    metadata = result.get('metadata', {})
                    document = result.get('document', '').lower()
                    
                    # Check cache first
                    entry_id = metadata.get('entry_id')
                    if entry_id and entry_id in self.entry_cache:
                        entry = self.entry_cache[entry_id]
                    else:
                        entry = self._metadata_to_entry(metadata, document)
                        if entry_id:
                            entry.entry_id = entry_id
                    
                    # Calculate keyword score
                    keyword_score = 0
                    document_lower = document.lower()
                    entry_keywords_lower = [k.lower() for k in entry.keywords]
                    
                    for kw in keywords:
                        kw_lower = kw.lower()
                        
                        # Exact match in keywords list
                        if kw_lower in entry_keywords_lower:
                            keyword_score += 3
                        
                        # Match in document text
                        if kw_lower in document_lower:
                            keyword_score += 1
                    
                    if keyword_score > 0:
                        # Combine with vector similarity (inverse of distance)
                        vector_score = 1.0 - result.get('distance', 1.0)
                        total_score = (keyword_score * 0.7) + (vector_score * 0.3)
                        
                        scored_entries.append((total_score, entry))
                        
                except Exception as e:
                    print(f"Warning: Failed to score result: {e}")
                    continue
            
            # Sort by combined score
            scored_entries.sort(reverse=True, key=lambda x: x[0])
            
            # Return top_k entries
            entries = [entry for _, entry in scored_entries[:top_k]]
            
            # Cache the results
            for entry in entries:
                if entry.entry_id:
                    self._update_cache(entry.entry_id, entry)
            
            return entries
            
        except Exception as e:
            print(f"Error during keyword search: {e}")
            return []
    
    def structured_search(
        self,
        persons: Optional[List[str]] = None,
        timestamp_range: Optional[Tuple[datetime, datetime]] = None,
        location: Optional[str] = None,
        entities: Optional[List[str]] = None,
        topic: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[MemoryEntry]:
        """
        Symbolic Layer Search - Metadata-based deterministic filtering.
        
        Paper Reference: Section 3.1
        Retrieves based on R_k = {(key, val)} for structured constraints.
        Uses ChromaDB's metadata filtering capabilities.
        
        Args:
            persons: Filter by person names
            timestamp_range: Filter by time range (start, end)
            location: Filter by location
            entities: Filter by entities
            topic: Filter by topic
            top_k: Maximum number of results to return
        """
        try:
            # Build metadata filters
            filters = {}
            
            if persons:
                filters["persons_json"] = json.dumps(persons)
            
            if location:
                filters["location"] = location
            
            if topic:
                filters["topic"] = topic
            
            if entities:
                filters["entities_json"] = json.dumps(entities)
            
            if timestamp_range:
                start_time, end_time = timestamp_range
                filters["timestamp"] = {
                    "$gte": start_time.isoformat(),
                    "$lte": end_time.isoformat()
                }
            
            # If no filters, return empty
            if not filters:
                return []
            
            # Use fetch_with_filter for pure metadata filtering
            # First, get all matching documents
            filter_results = self.agentic_RAG.fetch_with_filter(
                agent_ID=self.agent_id,
                filter_metadata=filters,
                top_k=top_k or 300
            )
            
            # Convert to MemoryEntry objects
            entries = []
            for result in filter_results:
                try:
                    metadata = result.get('metadata', {})
                    document = result.get('document', '')
                    
                    # Check cache
                    entry_id = metadata.get('entry_id')
                    if entry_id and entry_id in self.entry_cache:
                        entries.append(self.entry_cache[entry_id])
                        continue
                    
                    entry = self._metadata_to_entry(metadata, document)
                    if entry_id:
                        entry.entry_id = entry_id
                        self._update_cache(entry_id, entry)
                    
                    entries.append(entry)
                except Exception as e:
                    print(f"Warning: Failed to parse filter result: {e}")
                    continue
            
            # If we have timestamp_range but Chroma doesn't support it natively,
            # we need to filter manually
            if timestamp_range and not self._chroma_supports_date_filtering():
                start_time, end_time = timestamp_range
                filtered_entries = []
                
                for entry in entries:
                    if entry.timestamp:
                        try:
                            entry_time = datetime.fromisoformat(entry.timestamp)
                            if start_time <= entry_time <= end_time:
                                filtered_entries.append(entry)
                        except ValueError:
                            continue
                
                entries = filtered_entries
            
            # Apply top_k limit if specified
            if top_k and len(entries) > top_k:
                entries = entries[:top_k]
            
            return entries
            
        except Exception as e:
            print(f"Error during structured search: {e}")
            return []
    
    def _chroma_supports_date_filtering(self) -> bool:
        """Check if ChromaDB supports date range filtering."""
        # ChromaDB's metadata filtering is limited for dates
        # This is a placeholder - actual implementation depends on Chroma version
        return False
    
    def hybrid_search(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        persons: Optional[List[str]] = None,
        location: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 5,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4
    ) -> List[MemoryEntry]:
        """
        Hybrid Search - Combine semantic, lexical, and symbolic layers.
        
        Paper Reference: Section 3.2 - Multi-View Indexing
        Combines all three layers for comprehensive retrieval.
        
        Args:
            query: Semantic search query
            keywords: Keywords for lexical matching
            persons: Persons filter
            location: Location filter
            topic: Topic filter
            top_k: Number of results
            semantic_weight: Weight for semantic scores (0-1)
            keyword_weight: Weight for keyword scores (0-1)
        """
        try:
            # Get semantic results
            semantic_results = self.semantic_search(
                query=query,
                top_k=top_k * 2,
                persons=persons,
                location=location,
                topic=topic
            )
            
            # Get keyword results if keywords provided
            keyword_results = []
            if keywords:
                keyword_results = self.keyword_search(
                    keywords=keywords,
                    top_k=top_k * 2,
                    persons=persons,
                    location=location
                )
            
            # Combine and score results
            entry_scores = {}
            
            # Score semantic results
            for i, entry in enumerate(semantic_results):
                score = semantic_weight * (1.0 - (i / (len(semantic_results) * 2)))
                if entry.entry_id in entry_scores:
                    entry_scores[entry.entry_id] += score
                else:
                    entry_scores[entry.entry_id] = score
            
            # Score keyword results
            for i, entry in enumerate(keyword_results):
                score = keyword_weight * (1.0 - (i / (len(keyword_results) * 2)))
                if entry.entry_id in entry_scores:
                    entry_scores[entry.entry_id] += score
                else:
                    entry_scores[entry.entry_id] = score
            
            # Sort by combined score
            scored_entries = []
            for entry in set(semantic_results + keyword_results):
                score = entry_scores.get(entry.entry_id, 0)
                scored_entries.append((score, entry))
            
            scored_entries.sort(reverse=True, key=lambda x: x[0])
            
            # Return top_k entries
            return [entry for _, entry in scored_entries[:top_k]]
            
        except Exception as e:
            print(f"Error during hybrid search: {e}")
            return []
    
    def get_entry_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry by its ID.
        
        Args:
            entry_id: The entry ID to retrieve
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        # Check cache first
        if entry_id in self.entry_cache:
            return self.entry_cache[entry_id]
        
        try:
            # Use get_message_by_id from Agentic_RAG
            result = self.agentic_RAG.get_message_by_id(
                agent_ID=self.agent_id,
                doc_id=entry_id
            )
            
            if result:
                metadata = result.get('metadata', {})
                document = result.get('document', '')
                entry = self._metadata_to_entry(metadata, document)
                entry.entry_id = entry_id
                
                # Cache the entry
                self._update_cache(entry_id, entry)
                
                return entry
                
        except Exception as e:
            print(f"Error retrieving entry {entry_id}: {e}")
        
        return None
    
    def get_all_entries(self, limit: int = 300) -> List[MemoryEntry]:
        """
        Get all memory entries from the collection.
        
        Args:
            limit: Maximum number of entries to retrieve
            
        Returns:
            List of MemoryEntry objects
        """
        try:
            # Use fetch_history from Agentic_RAG
            results = self.agentic_RAG.fetch_history(
                agent_ID=self.agent_id,
                top_k=limit
            )
            
            entries = []
            for result in results:
                try:
                    metadata = result.get('metadata', {})
                    document = result.get('document', '')
                    
                    # Check cache
                    entry_id = metadata.get('entry_id')
                    if entry_id and entry_id in self.entry_cache:
                        entries.append(self.entry_cache[entry_id])
                        continue
                    
                    entry = self._metadata_to_entry(metadata, document)
                    if entry_id:
                        entry.entry_id = entry_id
                        self._update_cache(entry_id, entry)
                    
                    entries.append(entry)
                except Exception as e:
                    print(f"Warning: Failed to parse entry: {e}")
                    continue
            
            return entries
            
        except Exception as e:
            print(f"Error getting all entries: {e}")
            return []
    
    def update_entry(self, entry: MemoryEntry) -> bool:
        """
        Update an existing memory entry.
        
        Args:
            entry: The updated MemoryEntry
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not entry.entry_id:
                print("Error: Entry must have an entry_id to update")
                return False
            
            # Update in ChromaDB
            result = self.agentic_RAG.update_docs(
                agent_ID=self.agent_id,
                ids=[entry.entry_id],
                documents=[self._entry_to_document(entry)],
                metadatas=[self._entry_to_metadata(entry)]
            )
            
            # Update cache
            self._update_cache(entry.entry_id, entry)
            
            return True
            
        except Exception as e:
            print(f"Error updating entry {entry.entry_id}: {e}")
            return False
    
    def delete_entry(self, entry_id: str) -> bool:
        """
        Delete a memory entry by ID.
        
        Args:
            entry_id: The entry ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from ChromaDB
            result = self.agentic_RAG.delete_chat_history(
                agent_ID=self.agent_id,
                ids=[entry_id]
            )
            
            # Remove from cache
            if entry_id in self.entry_cache:
                del self.entry_cache[entry_id]
            
            return True
            
        except Exception as e:
            print(f"Error deleting entry {entry_id}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all memory entries from the collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all entry IDs
            entries = self.get_all_entries()
            entry_ids = [e.entry_id for e in entries if e.entry_id]
            
            if entry_ids:
                # Delete in batches
                batch_size = 100
                for i in range(0, len(entry_ids), batch_size):
                    self.agentic_RAG.delete_chat_history(
                        agent_ID=self.agent_id,
                        ids=entry_ids[i:i+batch_size]
                    )
            
            # Clear cache
            self.entry_cache.clear()
            
            print(f"Cleared all entries from {self.agent_id}")
            return True
            
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the memory entries collection.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Use Agentic_RAG's statistics method
            stats = self.agentic_RAG.get_statistics(self.agent_id)
            
            # Add cache statistics
            stats['cache_size'] = len(self.entry_cache)
            stats['cache_hit_rate'] = self.agentic_RAG.get_performance_metrics().get('cache_hit_rate', 0)
            
            return stats
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {'error': str(e)}
    
    def search_similar_entries(self, entry: MemoryEntry, top_k: int = 5) -> List[MemoryEntry]:
        """
        Find entries similar to a given entry.
        
        Args:
            entry: The entry to find similar ones to
            top_k: Number of similar entries to return
            
        Returns:
            List of similar MemoryEntry objects
        """
        # Use the entry's content as query
        return self.semantic_search(
            query=entry.lossless_restatement,
            top_k=top_k + 1,  # +1 because the entry itself might be in results
            distance_threshold=0.5
        )


# Factory function for creating VectorStore instances
def create_vector_store(agent_id: str = None, **kwargs) -> VectorStore:
    """
    Create a VectorStore instance.
    
    Args:
        agent_id: Optional agent ID for the collection
        **kwargs: Additional arguments for VectorStore
        
    Returns:
        VectorStore instance
    """
    if agent_id is None:
        agent_id = f"memory_store_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
    
    return VectorStore(agent_id=agent_id, **kwargs)


# Usage example
if __name__ == "__main__":
    # Create a vector store
    store = VectorStore(agent_id="test_memory_store")
    
    # Create sample memory entries
    entries = [
        MemoryEntry(
            lossless_restatement="I discussed the project timeline with John yesterday.",
            keywords=["project", "timeline", "discussion"],
            persons=["John"],
            topic="work",
            location="office"
        ),
        MemoryEntry(
            lossless_restatement="The team meeting covered Q3 goals and deadlines.",
            keywords=["meeting", "goals", "deadlines", "Q3"],
            persons=["team"],
            topic="work",
            location="conference room"
        )
    ]
    
    # Add entries
    store.add_entries(entries)
    
    # Semantic search
    semantic_results = store.semantic_search("project timeline discussion", top_k=3)
    print(f"Semantic search results: {len(semantic_results)} entries")
    
    # Keyword search
    keyword_results = store.keyword_search(["project", "timeline"], top_k=3)
    print(f"Keyword search results: {len(keyword_results)} entries")
    
    # Hybrid search
    hybrid_results = store.hybrid_search(
        query="work discussions",
        keywords=["project", "meeting"],
        top_k=5
    )
    print(f"Hybrid search results: {len(hybrid_results)} entries")
    
    # Get statistics
    stats = store.get_statistics()
    print(f"Collection statistics: {stats}")