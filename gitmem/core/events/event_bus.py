"""
GitMem v2.0 — Event Bus (CENTRAL)

Central event bus for real-time updates and inter-module communication.
All SDK operations emit events through this bus, which are then:
1. Persisted to the Event Store (gitmem_events)
2. Pushed to connected clients via WebSocket
3. Picked up by background workers (if configured)
"""

from datetime import datetime
from typing import Any, Dict, List, Callable, Optional
from dataclasses import dataclass, field
import threading
import json
from gitmem.core.models import EventType, GitMemEvent


@dataclass
class Event:
    """Represents an in-memory event in the system (legacy compat & bus passing)."""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if hasattr(self.type, 'value') else str(self.type),
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
        key = event_type.value if hasattr(event_type, 'value') else str(event_type)
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)
    
    def subscribe_all(self, callback: Callable[[Event], None]):
        """Subscribe to all events."""
        self._global_listeners.append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Unsubscribe from specific event type."""
        key = event_type.value if hasattr(event_type, 'value') else str(event_type)
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
        key = event.type.value if hasattr(event.type, 'value') else str(event.type)
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


# ============================================================
# Helper Functions for V2 Events
# ============================================================

def emit_memory_created(agent_id: str, memory_id: str, memory_type: str, content: str, workspace_id: str, visibility: str = "private"):
    """Emit memory created event."""
    event_bus.emit_simple(
        EventType.MEMORY_CREATED,
        {
            "workspace_id": workspace_id,
            "memory_id": memory_id,
            "memory_type": memory_type,
            "content": content[:100] + ("..." if len(content) > 100 else ""),
            "visibility": visibility
        },
        agent_id=agent_id
    )

def emit_commit_created(agent_id: str, commit_hash: str, message: str, workspace_id: str, parent_hash: Optional[str] = None):
    """Emit commit created event."""
    event_bus.emit_simple(
        EventType.COMMIT_CREATED,
        {
            "workspace_id": workspace_id,
            "commit_hash": commit_hash,
            "message": message,
            "parent_hash": parent_hash
        },
        agent_id=agent_id
    )
