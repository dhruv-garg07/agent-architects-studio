"""
GitMem v2.0 — Event Store

Persists immutable events to gitmem_events table.
Powers: activity feeds, debugging, analytics, undo, audit, realtime collaboration.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from gitmem.core.models import GitMemEvent, EventType


class EventStore:
    """Persists events to Supabase gitmem_events table."""

    def __init__(self, supabase_client):
        self.client = supabase_client
        self._table = "gitmem_events"

    def append(self, event: GitMemEvent) -> None:
        """Persist a single event."""
        if not self.client:
            return
        try:
            data = event.model_dump(mode='json')
            # Convert enum to string
            if hasattr(data.get('event_type'), 'value'):
                data['event_type'] = data['event_type'].value
            self.client.table(self._table).insert(data).execute()
        except Exception as e:
            print(f"[EventStore] Failed to persist event: {e}")

    def emit_and_persist(self, workspace_id: str, event_type: EventType,
                         actor_id: str, entity_type: str, entity_id: str,
                         payload: Dict[str, Any] = None) -> GitMemEvent:
        """Create, persist, and return an event."""
        event = GitMemEvent(
            workspace_id=workspace_id,
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {}
        )
        self.append(event)
        return event

    def get_events(self, workspace_id: str, limit: int = 50,
                   event_type: Optional[str] = None,
                   entity_type: Optional[str] = None,
                   entity_id: Optional[str] = None) -> List[Dict]:
        """Query events with optional filters."""
        if not self.client:
            return []
        try:
            query = self.client.table(self._table).select("*") \
                .eq("workspace_id", workspace_id) \
                .order("created_at", desc=True)

            if event_type:
                query = query.eq("event_type", event_type)
            if entity_type:
                query = query.eq("entity_type", entity_type)
            if entity_id:
                query = query.eq("entity_id", entity_id)

            res = query.limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[EventStore] Query failed: {e}")
            return []

    def get_activity_feed(self, workspace_id: str, limit: int = 20) -> List[Dict]:
        """Get a mixed activity feed for the workspace."""
        return self.get_events(workspace_id, limit=limit)

    def get_entity_history(self, entity_type: str, entity_id: str,
                           limit: int = 50) -> List[Dict]:
        """Get all events for a specific entity (e.g., a memory or repo)."""
        if not self.client:
            return []
        try:
            res = self.client.table(self._table).select("*") \
                .eq("entity_type", entity_type) \
                .eq("entity_id", entity_id) \
                .order("created_at", desc=True) \
                .limit(limit).execute()
            return res.data or []
        except Exception as e:
            print(f"[EventStore] Entity history query failed: {e}")
            return []
