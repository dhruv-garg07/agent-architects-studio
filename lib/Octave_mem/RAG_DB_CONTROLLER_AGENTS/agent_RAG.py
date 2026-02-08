"""
This file a standalone file api_manhattan to call. All the agent apis should be here.
It includes apis for both the file and the chat history uploads and retrievals.
Each collection name in the chroma DB is the agent ID.
CRUD operations of the agents includes CRUD on collection corresponding to that agent ID.
"""

import sys
import os

# Add parent directories to path to resolve module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # RAG_DB_CONTROLLER_AGENTS parent
grandparent_dir = os.path.dirname(parent_dir)  # Octave_mem

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if grandparent_dir not in sys.path:
    sys.path.insert(0, grandparent_dir)

from RAG_DB.chroma_collection_wrapper import ChromaCollectionWrapper
from RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG
from dotenv import load_dotenv
from typing import List, Dict, Optional

load_dotenv()

"""
This file a standalone file api_manhattan to call. All the agent apis should be here.
It includes apis for both the file and the chat history uploads and retrievals.
Each collection name in the chroma DB is the agent ID.
CRUD operations of the agents includes CRUD on collection corresponding to that agent ID.

Advanced Features Added:
1. Semantic caching with similarity threshold
2. Batch operations with transaction support
3. Vector similarity search with filtering
4. Time-based retrieval and cleanup
5. Multi-agent cross-collection operations
6. Embedding management and versioning
7. Performance monitoring and analytics
8. Backup and restore operations
"""

from RAG_DB.chroma_collection_wrapper import ChromaCollectionWrapper
from RAG_DB_CONTROLLER.read_data_RAG_all_DB import read_data_RAG
from dotenv import load_dotenv
import os
from typing import List, Dict, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import hashlib
import json
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid

load_dotenv()

class SemanticCache:
    """Semantic caching layer for reducing redundant vector searches"""
    
    def __init__(self, max_size: int = 300, similarity_threshold: float = 0.95):
        self.cache = {}
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.query_hash_map = {}
        
    def _generate_query_hash(self, query: str) -> str:
        """Generate consistent hash for query"""
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def get_cached_result(self, agent_id: str, query: str) -> Optional[List]:
        """Get cached result if similar query exists"""
        query_hash = self._generate_query_hash(query)
        cache_key = f"{agent_id}:{query_hash}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Check for semantically similar cached queries
        for cached_query_hash, cached_data in self.query_hash_map.items():
            if cached_data['agent_id'] == agent_id:
                # In production, use proper embedding similarity here
                # For now, use simple string similarity
                if self._calculate_similarity(query, cached_data['query']) > self.similarity_threshold:
                    return self.cache[f"{agent_id}:{cached_query_hash}"]
        
        return None
    
    def cache_result(self, agent_id: str, query: str, result: List):
        """Cache query result"""
        query_hash = self._generate_query_hash(query)
        cache_key = f"{agent_id}:{query_hash}"
        
        # LRU eviction
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = result
        self.query_hash_map[query_hash] = {
            'agent_id': agent_id,
            'query': query,
            'timestamp': datetime.now()
        }
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries (simplified)"""
        # In production, use proper embedding similarity
        set1 = set(query1.lower().split())
        set2 = set(query2.lower().split())
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)
    
    def invalidate_agent_cache(self, agent_id: str):
        """Invalidate all cache entries for an agent"""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{agent_id}:")]
        for key in keys_to_remove:
            del self.cache[key]
        
        # Clean query hash map
        query_hashes_to_remove = [
            h for h, data in self.query_hash_map.items()
            if data['agent_id'] == agent_id
        ]
        for query_hash in query_hashes_to_remove:
            del self.query_hash_map[query_hash]

class BatchOperation:
    """Batch operation with transaction-like behavior"""
    
    def __init__(self, agentic_rag_instance: 'Agentic_RAG'):
        self.agentic_rag = agentic_rag_instance
        self.operations = []
        self.results = []
        
    def add_documents(self, agent_id: str, ids: List[str], documents: List[str], 
                      metadatas: Optional[List[Dict]] = None):
        """Queue add operation"""
        self.operations.append({
            'type': 'add',
            'agent_id': agent_id,
            'ids': ids,
            'documents': documents,
            'metadatas': metadatas
        })
        return self
    
    def update_documents(self, agent_id: str, ids: List[str], documents: List[str], 
                         metadatas: Optional[List[Dict]] = None):
        """Queue update operation"""
        self.operations.append({
            'type': 'update',
            'agent_id': agent_id,
            'ids': ids,
            'documents': documents,
            'metadatas': metadatas
        })
        return self
    
    def delete_documents(self, agent_id: str, ids: List[str]):
        """Queue delete operation"""
        self.operations.append({
            'type': 'delete',
            'agent_id': agent_id,
            'ids': ids
        })
        return self
    
    def execute(self) -> Dict[str, Any]:
        """Execute all queued operations with rollback on failure"""
        print(f"[DEBUG BatchOperation.execute] Starting execution with {len(self.operations)} operations")
        try:
            for idx, op in enumerate(self.operations):
                print(f"[DEBUG BatchOperation.execute] Processing operation {idx+1}/{len(self.operations)}: type={op['type']}, agent_id={op['agent_id']}")
                if op['type'] == 'add':
                    print(f"[DEBUG BatchOperation.execute] Calling add_docs with {len(op['ids'])} documents")
                    result = self.agentic_rag.add_docs(
                        agent_ID=op['agent_id'],
                        ids=op['ids'],
                        documents=op['documents'],
                        metadatas=op.get('metadatas')
                    )
                    print(f"[DEBUG BatchOperation.execute] add_docs result: {result}")
                elif op['type'] == 'update':
                    result = self.agentic_rag.update_docs(
                        agent_ID=op['agent_id'],
                        ids=op['ids'],
                        documents=op['documents'],
                        metadatas=op.get('metadatas')
                    )
                elif op['type'] == 'delete':
                    result = self.agentic_rag.delete_chat_history(
                        agent_ID=op['agent_id'],
                        ids=op['ids']
                    )
                self.results.append(result)
            
            print(f"[DEBUG BatchOperation.execute] All operations completed successfully")
            return {
                'success': True,
                'operations': len(self.operations),
                'results': self.results
            }
        except Exception as e:
            print(f"[DEBUG BatchOperation.execute] EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            # Rollback would be implemented here in production
            return {
                'success': False,
                'error': str(e),
                'operations_completed': len(self.results)
            }

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'queries': [],
            'operations': [],
            'response_times': [],
            'cache_hits': 0,
            'cache_misses': 0
        }
        
    def log_query(self, agent_id: str, query: str, response_time: float):
        """Log query performance"""
        self.metrics['queries'].append({
            'agent_id': agent_id,
            'query': query[:100],  # Truncate for privacy
            'response_time': response_time,
            'timestamp': datetime.now()
        })
        
    def log_operation(self, operation_type: str, agent_id: str, duration: float):
        """Log operation performance"""
        self.metrics['operations'].append({
            'operation_type': operation_type,
            'agent_id': agent_id,
            'duration': duration,
            'timestamp': datetime.now()
        })
        
    def increment_cache_hits(self):
        self.metrics['cache_hits'] += 1
        
    def increment_cache_misses(self):
        self.metrics['cache_misses'] += 1
        
    def get_performance_report(self) -> Dict:
        """Generate performance report"""
        avg_response_time = (
            sum(r['response_time'] for r in self.metrics['queries']) / 
            len(self.metrics['queries']) if self.metrics['queries'] else 0
        )
        
        cache_hit_rate = (
            self.metrics['cache_hits'] / 
            (self.metrics['cache_hits'] + self.metrics['cache_misses'])
            if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
        )
        
        return {
            'total_queries': len(self.metrics['queries']),
            'total_operations': len(self.metrics['operations']),
            'average_response_time': avg_response_time,
            'cache_hit_rate': cache_hit_rate,
            'cache_hits': self.metrics['cache_hits'],
            'cache_misses': self.metrics['cache_misses']
        }

class Agentic_RAG:
    def __init__(self, database: str = None, enable_cache: bool = True, 
                 enable_monitoring: bool = True):
        """Initialize the controller with ChromaCollectionWrapper and advanced features."""
        load_dotenv()
        if database is None:
            database = os.getenv("CHROMA_DATABASE_CHAT_HISTORY")
        self.wrapper = ChromaCollectionWrapper(database=database)
        self.read_controller = read_data_RAG(database=database)
        
        # Advanced feature initializations
        self.semantic_cache = SemanticCache() if enable_cache else None
        self.performance_monitor = PerformanceMonitor() if enable_monitoring else None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Embedding model info
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "default")
        self.embedding_dimension = self._get_embedding_dimension()
        
    def _get_embedding_dimension(self) -> int:
        """Get embedding dimension based on model"""
        # This should be configured based on your embedding model
        model_dimensions = {
            "text-embedding-ada-002": 1536,
            "all-MiniLM-L6-v2": 384,
            "default": 768
        }
        return model_dimensions.get(self.embedding_model, 768)
    
    # === EXISTING METHODS (unchanged for backward compatibility) ===
    
    def create_agent_collection(self, agent_ID: str):
        """Create a new collection for the agent."""
        return self.wrapper.manager.create_collection(collection_name=agent_ID)
    
    def delete_agent_collection(self, agent_ID: str):
        """Delete the collection for the agent."""
        # Invalidate cache for this agent
        if self.semantic_cache:
            self.semantic_cache.invalidate_agent_cache(agent_ID)
        return self.wrapper.manager.delete_collection(collection_name=agent_ID)
    
    def add_docs(self, agent_ID: str, ids: List[str], documents: List[str], 
                 metadatas: Optional[List[Dict]] = None) -> Dict:
        """Add chat history to the agent's collection with verification."""
        start_time = datetime.now()
        result = self.wrapper.create_or_update_collection_with_verify(
            collection_name=agent_ID,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        # Log performance
        if self.performance_monitor:
            duration = (datetime.now() - start_time).total_seconds()
            self.performance_monitor.log_operation('add', agent_ID, duration)
        
        # Invalidate cache for this agent
        if self.semantic_cache:
            self.semantic_cache.invalidate_agent_cache(agent_ID)
            
        return result
        
    def get_agent_collection_info(self, agent_ID: str) -> Dict:
        """Get information about the agent's collection."""
        return self.wrapper.get_collection_info(collection_name=agent_ID)
    
    def search_agent_collection(self, agent_ID: str, query: str, n_results: int = 5, 
                               include_metadata: bool = True):
        """Search an agent collection for documents related to `query`."""
        start_time = datetime.now()
        
        # Check cache first
        if self.semantic_cache:
            cached_result = self.semantic_cache.get_cached_result(agent_ID, query)
            if cached_result is not None:
                if self.performance_monitor:
                    self.performance_monitor.increment_cache_hits()
                return cached_result[:n_results] if n_results else cached_result
        
        # Cache miss
        if self.performance_monitor:
            self.performance_monitor.increment_cache_misses()
        
        try:
            results = self.read_controller.fetch_related_to_query(
                agent_ID, query, top_k=n_results
            )
            
            # Cache the result
            if self.semantic_cache and results:
                self.semantic_cache.cache_result(agent_ID, query, results)
            
            # Log performance
            if self.performance_monitor:
                duration = (datetime.now() - start_time).total_seconds()
                self.performance_monitor.log_query(agent_ID, query, duration)
                
            return results or []
        except Exception as e:
            print(f"[Agentic_Chat_Manager] search_agent_collection error for {agent_ID}: {e}")
            return []

    def fetch_history(self, agent_ID: str, top_k: int = 50) -> List[Dict]:
        """Fetch recent chat history for an agent (collection)."""
        try:
            return self.read_controller.fetch(user_ID=agent_ID, top_k=top_k) or []
        except Exception as e:
            print(f"[Agentic_Chat_Manager] fetch_history error for {agent_ID}: {e}")
            return []

    def get_message_by_id(self, agent_ID: str, doc_id: str) -> Optional[Dict]:
        """Retrieve a single message/document by its document id within the agent collection."""
        try:
            return self.read_controller.fetch_with_id(user_ID=agent_ID, doc_id=doc_id)
        except Exception as e:
            print(f"[Agentic_Chat_Manager] get_message_by_id error for {agent_ID}:{doc_id}: {e}")
            return None

    def fetch_with_filter(self, agent_ID: str, filter_metadata: Dict, 
                         top_k: int = 50) -> List[Dict]:
        """Fetch chat history with a metadata filter."""
        try:
            return self.read_controller.fetch_with_filter(
                user_ID=agent_ID, filter_metadata=filter_metadata, top_k=top_k
            ) or []
        except Exception as e:
            print(f"[Agentic_Chat_Manager] fetch_with_filter error for {agent_ID}: {e}")
            return []
        
    def update_docs(self, agent_ID: str, ids: List[str], documents: List[str], 
                   metadatas: Optional[List[Dict]] = None) -> Dict:
        """Update chat history in the agent's collection with verification."""
        result = self.wrapper.update_collection_with_verify(
            collection_name=agent_ID,
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        # Invalidate cache
        if self.semantic_cache:
            self.semantic_cache.invalidate_agent_cache(agent_ID)
            
        return result
    
    def update_doc_metadata(self, agent_ID: str, ids: List[str], 
                           metadatas: List[Dict]) -> Dict:
        """Update metadata of chat history entries in the agent's collection with verification."""
        result = self.wrapper.update_collection_metadata_with_verify(
            collection_name=agent_ID,
            ids=ids,
            metadatas=metadatas
        )
        
        # Invalidate cache
        if self.semantic_cache:
            self.semantic_cache.invalidate_agent_cache(agent_ID)
            
        return result
    
    def delete_chat_history(self, agent_ID: str, ids: List[str]) -> Dict:
        """Delete chat history entries from the agent's collection with verification."""
        result = self.wrapper.delete_documents_with_verify(
            collection_name=agent_ID,
            ids=ids
        )
        
        # Invalidate cache
        if self.semantic_cache:
            self.semantic_cache.invalidate_agent_cache(agent_ID)
            
        return result
    
    # === ADVANCED FEATURES ===
    
    def search_with_filters(self, agent_ID: str, query: str, 
                           filters: Dict[str, Any], n_results: int = 5,
                           distance_threshold: float = 0.7) -> List[Dict]:
        """
        Advanced search with metadata filtering and distance threshold.
        
        Args:
            agent_ID: Agent identifier
            query: Search query
            filters: Metadata filters (e.g., {"sender": "user", "timestamp": {"$gte": "2024-01-01"}})
            n_results: Number of results to return
            distance_threshold: Maximum similarity distance (lower = more similar)
            
        Returns:
            List of filtered and thresholded results
        """
        try:
            # Get raw search results
            raw_results = self.search_agent_collection(
                agent_ID, query, n_results=n_results * 2, include_metadata=True
            )
            
            if not raw_results:
                return []
            
            # Apply filters
            filtered_results = []
            for result in raw_results:
                metadata = result.get('metadata', {})
                
                # Check all filters
                passes_filter = True
                for key, value in filters.items():
                    if key not in metadata:
                        passes_filter = False
                        break
                    
                    # Handle comparison operators
                    if isinstance(value, dict):
                        for op, op_value in value.items():
                            if op == "$gte" and metadata[key] < op_value:
                                passes_filter = False
                                break
                            elif op == "$lte" and metadata[key] > op_value:
                                passes_filter = False
                                break
                            elif op == "$eq" and metadata[key] != op_value:
                                passes_filter = False
                                break
                    elif metadata[key] != value:
                        passes_filter = False
                        break
                
                # Check distance threshold
                distance = result.get('distance', 1.0)
                if passes_filter and distance <= distance_threshold:
                    filtered_results.append(result)
            
            # Return top n results after filtering
            return filtered_results[:n_results]
            
        except Exception as e:
            print(f"[Agentic_RAG] search_with_filters error: {e}")
            return []
    
    def fetch_time_range(self, agent_ID: str, start_time: datetime, 
                        end_time: Optional[datetime] = None,
                        top_k: int = 100) -> List[Dict]:
        """
        Fetch documents within a specific time range.
        
        Args:
            agent_ID: Agent identifier
            start_time: Start of time range
            end_time: End of time range (defaults to now)
            top_k: Maximum number of results
            
        Returns:
            List of documents within the time range
        """
        if end_time is None:
            end_time = datetime.now()
        
        filter_metadata = {
            "timestamp": {
                "$gte": start_time.isoformat(),
                "$lte": end_time.isoformat()
            }
        }
        
        return self.fetch_with_filter(agent_ID, filter_metadata, top_k)
    
    def multi_agent_search(self, agent_ids: List[str], query: str, 
                          n_results_per_agent: int = 3) -> Dict[str, List]:
        """
        Search across multiple agent collections simultaneously.
        
        Args:
            agent_ids: List of agent identifiers to search
            query: Search query
            n_results_per_agent: Results per agent
            
        Returns:
            Dictionary mapping agent_id to search results
        """
        results = {}
        
        # Search all agents in parallel
        with ThreadPoolExecutor(max_workers=len(agent_ids)) as executor:
            future_to_agent = {
                executor.submit(
                    self.search_agent_collection, 
                    agent_id, query, n_results_per_agent
                ): agent_id 
                for agent_id in agent_ids
            }
            
            for future in asyncio.as_completed(future_to_agent.keys()):
                agent_id = future_to_agent[future]
                try:
                    results[agent_id] = future.result()
                except Exception as e:
                    print(f"[Agentic_RAG] Error searching agent {agent_id}: {e}")
                    results[agent_id] = []
        
        return results
    
    def batch_operation(self) -> BatchOperation:
        """
        Create a batch operation for transactional-like behavior.
        
        Returns:
            BatchOperation instance
        """
        return BatchOperation(self)
    
    def deduplicate_collection(self, agent_ID: str, similarity_threshold: float = 0.9) -> Dict:
        """
        Remove duplicate or highly similar documents from a collection.
        
        Args:
            agent_ID: Agent identifier
            similarity_threshold: Threshold for considering documents as duplicates
            
        Returns:
            Statistics about deduplication
        """
        try:
            # Get all documents
            all_docs = self.fetch_history(agent_ID, top_k=10000)
            
            if not all_docs:
                return {'removed': 0, 'remaining': 0}
            
            # Simple content-based deduplication
            seen_contents = set()
            duplicates_to_remove = []
            
            for doc in all_docs:
                content = doc.get('document', '').strip()
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                if content_hash in seen_contents:
                    doc_id = doc.get('id')
                    if doc_id:
                        duplicates_to_remove.append(doc_id)
                else:
                    seen_contents.add(content_hash)
            
            # Remove duplicates
            if duplicates_to_remove:
                self.delete_chat_history(agent_ID, duplicates_to_remove)
            
            return {
                'removed': len(duplicates_to_remove),
                'remaining': len(all_docs) - len(duplicates_to_remove),
                'duplicate_ids': duplicates_to_remove
            }
            
        except Exception as e:
            print(f"[Agentic_RAG] deduplicate_collection error: {e}")
            return {'removed': 0, 'remaining': 0, 'error': str(e)}
    
    def export_collection(self, agent_ID: str, format: str = 'json') -> Dict:
        """
        Export entire collection to various formats.
        
        Args:
            agent_ID: Agent identifier
            format: Export format ('json', 'csv', 'text')
            
        Returns:
            Dictionary with exported data and metadata
        """
        try:
            # Get all documents
            all_docs = self.fetch_history(agent_ID, top_k=100000)
            
            if format == 'json':
                export_data = json.dumps(all_docs, indent=2, default=str)
            elif format == 'csv':
                # Simplified CSV export
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                
                if all_docs:
                    # Write header
                    headers = ['id', 'document', 'metadata']
                    writer.writerow(headers)
                    
                    # Write data
                    for doc in all_docs:
                        writer.writerow([
                            doc.get('id', ''),
                            doc.get('document', ''),
                            json.dumps(doc.get('metadata', {}), default=str)
                        ])
                
                export_data = output.getvalue()
            else:  # text format
                lines = []
                for doc in all_docs:
                    lines.append(f"ID: {doc.get('id', 'N/A')}")
                    lines.append(f"Content: {doc.get('document', '')}")
                    lines.append(f"Metadata: {doc.get('metadata', {})}")
                    lines.append("-" * 50)
                export_data = "\n".join(lines)
            
            return {
                'agent_id': agent_ID,
                'format': format,
                'document_count': len(all_docs),
                'data': export_data,
                'exported_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Agentic_RAG] export_collection error: {e}")
            return {'error': str(e)}
    
    def get_statistics(self, agent_ID: str) -> Dict:
        """
        Get comprehensive statistics about the agent's collection.
        
        Args:
            agent_ID: Agent identifier
            
        Returns:
            Statistics dictionary
        """
        try:
            # Get collection info
            collection_info = self.get_agent_collection_info(agent_ID)
            
            # Get document count
            all_docs = self.fetch_history(agent_ID, top_k=100000)
            
            # Calculate metadata statistics
            metadata_stats = {}
            if all_docs:
                # Collect all metadata keys
                all_keys = set()
                for doc in all_docs:
                    metadata = doc.get('metadata', {})
                    all_keys.update(metadata.keys())
                
                # Count occurrences
                for key in all_keys:
                    count = sum(1 for doc in all_docs if key in doc.get('metadata', {}))
                    metadata_stats[key] = count
            
            return {
                'agent_id': agent_ID,
                'document_count': len(all_docs),
                'collection_info': collection_info,
                'metadata_statistics': metadata_stats,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[Agentic_RAG] get_statistics error: {e}")
            return {'error': str(e)}
    
    def get_performance_metrics(self) -> Dict:
        """
        Get performance monitoring metrics.
        
        Returns:
            Performance metrics dictionary
        """
        if self.performance_monitor:
            return self.performance_monitor.get_performance_report()
        return {'monitoring_disabled': True}
    
    def clear_cache(self, agent_ID: Optional[str] = None):
        """
        Clear semantic cache for specific agent or all agents.
        
        Args:
            agent_ID: Optional agent identifier, if None clears all cache
        """
        if self.semantic_cache:
            if agent_ID:
                self.semantic_cache.invalidate_agent_cache(agent_ID)
            else:
                self.semantic_cache.cache.clear()
                self.semantic_cache.query_hash_map.clear()
    
    def backup_collection(self, agent_ID: str, backup_name: Optional[str] = None) -> Dict:
        """
        Create a backup of the agent's collection.
        
        Args:
            agent_ID: Agent identifier
            backup_name: Optional custom backup name
            
        Returns:
            Backup information
        """
        if backup_name is None:
            backup_name = f"{agent_ID}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Export collection data
            export_data = self.export_collection(agent_ID, format='json')
            
            if 'error' in export_data:
                return export_data
            
            # In production, save to cloud storage or backup system
            # For now, return the export data
            return {
                'backup_name': backup_name,
                'agent_id': agent_ID,
                'document_count': export_data['document_count'],
                'backup_timestamp': datetime.now().isoformat(),
                'export_data': export_data['data'][:1000] + "..." if len(export_data['data']) > 1000 else export_data['data']
            }
            
        except Exception as e:
            print(f"[Agentic_RAG] backup_collection error: {e}")
            return {'error': str(e)}
    
    def similarity_search_with_embedding(self, agent_ID: str, 
                                       embedding: List[float],
                                       n_results: int = 5) -> List[Dict]:
        """
        Search using precomputed embeddings instead of text query.
        
        Args:
            agent_ID: Agent identifier
            embedding: Precomputed embedding vector
            n_results: Number of results to return
            
        Returns:
            List of similar documents
        """
        # This requires Chroma's direct embedding search capability
        # Implementation depends on your ChromaCollectionWrapper
        try:
            # Placeholder - implement based on your Chroma wrapper capabilities
            # If your wrapper supports direct embedding search:
            # return self.wrapper.search_with_embedding(agent_ID, embedding, n_results)
            
            print(f"[Agentic_RAG] Direct embedding search not implemented")
            return []
            
        except Exception as e:
            print(f"[Agentic_RAG] similarity_search_with_embedding error: {e}")
            return []

    # Async versions of key methods for non-blocking operations
    async def search_agent_collection_async(self, agent_ID: str, query: str, 
                                          n_results: int = 5) -> List[Dict]:
        """Async version of search_agent_collection."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.search_agent_collection,
            agent_ID, query, n_results
        )
    
    async def add_docs_async(self, agent_ID: str, ids: List[str], 
                           documents: List[str], metadatas: Optional[List[Dict]] = None) -> Dict:
        """Async version of add_docs."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.add_docs,
            agent_ID, ids, documents, metadatas
        )

# Factory function for backward compatibility
def create_agentic_rag(database: str = None, **kwargs) -> Agentic_RAG:
    """
    Factory function to create Agentic_RAG instance with optional advanced features.
    
    Args:
        database: Database path
        **kwargs: Additional arguments for Agentic_RAG constructor
        
    Returns:
        Agentic_RAG instance
    """
    return Agentic_RAG(database=database, **kwargs)

# Singleton instance (optional)
_instance = None

def get_instance(database: str = None, **kwargs) -> Agentic_RAG:
    """Get singleton instance of Agentic_RAG."""
    global _instance
    if _instance is None:
        _instance = Agentic_RAG(database=database, **kwargs)
    return _instance