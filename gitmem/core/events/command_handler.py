"""
GitMem v2.0 — Command Handler

Central command dispatcher. All requests flow through here.
Pattern: REST API → Command Handler → Auth → Business Logic → Event Bus → Workers

This is the SPINE of the event-driven architecture.
"""

from typing import Any, Dict, Optional, Callable
from datetime import datetime
from gitmem.core.models import EventType, GitMemEvent


class CommandHandler:
    """
    Central command dispatcher for GitMem.
    
    All operations are routed as commands:
    1. Validate the command
    2. Authorize (via RBAC)
    3. Execute business logic
    4. Emit events
    5. Return result
    """

    def __init__(self, event_bus, event_store, auth=None, rbac=None):
        self.event_bus = event_bus
        self.event_store = event_store
        self.auth = auth
        self.rbac = rbac
        self._handlers: Dict[str, Callable] = {}

    def register(self, command_name: str, handler: Callable):
        """Register a command handler."""
        self._handlers[command_name] = handler

    def execute(self, command_name: str, actor_id: str,
                workspace_id: str, payload: Dict[str, Any] = None,
                skip_auth: bool = False) -> Dict[str, Any]:
        """
        Execute a command through the full pipeline.
        
        Returns: {"status": "success"|"error", "data": ..., "error": ...}
        """
        payload = payload or {}

        # 1. Validate command exists
        handler = self._handlers.get(command_name)
        if not handler:
            return {"status": "error", "error": f"Unknown command: {command_name}"}

        # 2. Authorize (if RBAC is configured)
        if self.rbac and not skip_auth:
            allowed = self.rbac.check_permission(
                actor_id=actor_id,
                workspace_id=workspace_id,
                action=command_name,
                resource=payload.get("resource_id")
            )
            if not allowed:
                return {"status": "error", "error": "Permission denied"}

        # 3. Execute
        try:
            result = handler(actor_id=actor_id, workspace_id=workspace_id, **payload)
        except Exception as e:
            # Emit error event
            self._emit_event(
                workspace_id=workspace_id,
                event_type=EventType.JOB_FAILED,
                actor_id=actor_id,
                entity_type="command",
                entity_id=command_name,
                payload={"error": str(e)}
            )
            return {"status": "error", "error": str(e)}

        # 4. Emit success event (commands can override by returning 'event' key)
        event_info = result.pop("_event", None) if isinstance(result, dict) else None
        if event_info:
            self._emit_event(
                workspace_id=workspace_id,
                event_type=event_info.get("type", EventType.JOB_COMPLETED),
                actor_id=actor_id,
                entity_type=event_info.get("entity_type", "command"),
                entity_id=event_info.get("entity_id", command_name),
                payload=event_info.get("payload", {})
            )

        return {"status": "success", "data": result}

    def _emit_event(self, workspace_id: str, event_type: EventType,
                    actor_id: str, entity_type: str, entity_id: str,
                    payload: Dict = None):
        """Emit event to bus and persist to store."""
        event = GitMemEvent(
            workspace_id=workspace_id,
            event_type=event_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {}
        )

        # Persist to event store
        if self.event_store:
            self.event_store.append(event)

        # Broadcast via event bus (WebSocket, workers, etc.)
        if self.event_bus:
            self.event_bus.emit_simple(
                event_type=event_type,
                data=event.model_dump(mode='json'),
                agent_id=actor_id
            )
