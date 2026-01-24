"""
GitMem Event Bus - Central event emitter for real-time updates.
All SDK operations emit events through this bus, which are then
pushed to connected clients via WebSocket.
"""

from datetime import datetime
from typing import Any, Dict, List, Callable, Optional
from enum import Enum
from dataclasses import dataclass, field
import threading
import json


class EventType(str, Enum):
    # Agent Events
    AGENT_HEARTBEAT = "agent:heartbeat"
    AGENT_ONLINE = "agent:online"
    AGENT_OFFLINE = "agent:offline"
    
    # Memory Events
    MEMORY_ADDED = "memory:added"
    MEMORY_UPDATED = "memory:updated"
    MEMORY_DELETED = "memory:deleted"
    
    # Commit Events  
    COMMIT_CREATED = "commit:created"
    COMMIT_REVERTED = "commit:reverted"
    
    # Index Events
    INDEX_UPDATED = "index:updated"
    INDEX_QUERY = "index:query"
    
    # Repo Events
    REPO_STARRED = "repo:starred"
    REPO_FORKED = "repo:forked"
    REPO_WATCHED = "repo:watched"
    RELEASE_CREATED = "release:created"
    
    # Context Events
    CONTEXT_QUERY = "context:query"
    
    # File Events
    FILE_UPLOADED = "file:uploaded"
    
    # Graph Events
    SEMANTIC_FACT_ADDED = "graph:fact_added"


@dataclass
class Event:
    """Represents a single event in the system."""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class EventBus:
    """
    Central event bus for GitMem real-time updates.
    Supports multiple listeners and thread-safe operations.
    """
    
    _instance: Optional['EventBus'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._listeners: Dict[str, List[Callable[[Event], None]]] = {}
        self._global_listeners: List[Callable[[Event], None]] = []
        self._event_history: List[Event] = []
        self._max_history = 100
        self._socketio = None  # Will be set when Flask-SocketIO is initialized
        self._initialized = True
    
    def set_socketio(self, socketio):
        """Inject Flask-SocketIO instance for WebSocket support."""
        self._socketio = socketio
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to specific event type."""
        key = event_type.value
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)
    
    def subscribe_all(self, callback: Callable[[Event], None]):
        """Subscribe to all events."""
        self._global_listeners.append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from specific event type."""
        key = event_type.value
        if key in self._listeners and callback in self._listeners[key]:
            self._listeners[key].remove(callback)
    
    def emit(self, event: Event):
        """
        Emit an event to all listeners.
        Also broadcasts via WebSocket if available.
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify type-specific listeners
        key = event.type.value
        if key in self._listeners:
            for callback in self._listeners[key]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"[EventBus] Error in listener: {e}")
        
        # Notify global listeners
        for callback in self._global_listeners:
            try:
                callback(event)
            except Exception as e:
                print(f"[EventBus] Error in global listener: {e}")
        
        # Broadcast via WebSocket
        if self._socketio:
            try:
                self._socketio.emit('gitmem_event', event.to_dict(), namespace='/gitmem')
            except Exception as e:
                print(f"[EventBus] WebSocket emit error: {e}")
    
    def emit_simple(self, event_type: EventType, data: Dict[str, Any], agent_id: Optional[str] = None):
        """Convenience method to emit events without creating Event object."""
        event = Event(type=event_type, data=data, agent_id=agent_id)
        self.emit(event)
    
    def get_recent_events(self, limit: int = 10, event_type: Optional[EventType] = None) -> List[Event]:
        """Get recent events from history."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]
    
    def clear_history(self):
        """Clear event history."""
        self._event_history = []


# Global singleton instance
event_bus = EventBus()


# Helper functions for common events
def emit_memory_added(agent_id: str, memory_id: str, memory_type: str, content: str, importance: float = 0.0, scope: str = "private"):
    """Emit memory added event."""
    event_bus.emit_simple(
        EventType.MEMORY_ADDED,
        {
            "memory_id": memory_id,
            "memory_type": memory_type,
            "content": content[:100] + ("..." if len(content) > 100 else ""),
            "importance": importance,
            "scope": scope
        },
        agent_id=agent_id
    )


def emit_commit_created(agent_id: str, commit_hash: str, message: str, parent_hash: Optional[str] = None):
    """Emit commit created event."""
    event_bus.emit_simple(
        EventType.COMMIT_CREATED,
        {
            "commit_hash": commit_hash,
            "message": message,
            "parent_hash": parent_hash
        },
        agent_id=agent_id
    )


def emit_agent_heartbeat(agent_id: str, model: Optional[str] = None, status: str = "online"):
    """Emit agent heartbeat event."""
    event_bus.emit_simple(
        EventType.AGENT_HEARTBEAT,
        {
            "status": status,
            "model": model,
            "last_active": datetime.now().isoformat()
        },
        agent_id=agent_id
    )


def emit_index_updated(embeddings_count: int, latency_ms: float):
    """Emit index update event."""
    event_bus.emit_simple(
        EventType.INDEX_UPDATED,
        {
            "embeddings": embeddings_count,
            "latency": f"{latency_ms:.1f}ms"
        }
    )


def emit_context_query(agent_id: str, query: str, tokens_used: int, memories_returned: int):
    """Emit context query event."""
    event_bus.emit_simple(
        EventType.CONTEXT_QUERY,
        {
            "query": query[:50] + ("..." if len(query) > 50 else ""),
            "tokens_used": tokens_used,
            "memories_returned": memories_returned
        },
        agent_id=agent_id
    )


def emit_release_created(version: str, description: str):
    """Emit release created event."""
    event_bus.emit_simple(
        EventType.RELEASE_CREATED,
        {
            "version": version,
            "description": description
        }
    )


def emit_semantic_fact_added(subject: str, predicate: str, obj: str, agent_id: Optional[str] = None):
    """Emit semantic fact (knowledge graph node) added."""
    event_bus.emit_simple(
        EventType.SEMANTIC_FACT_ADDED,
        {
            "subject": subject,
            "predicate": predicate,
            "object": obj
        },
        agent_id=agent_id
    )
