"""Helpers for governing inter-agent memory access and connection handshakes."""

import json
import os
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_PERMISSIONS = {"read", "write", "update", "delete"}
ALLOWED_SCOPES = {"all", "documents", "chat_history"}
FALLBACK_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    ".agent_connections_fallback.json",
)


def normalize_permissions(raw_permissions: Optional[List[str] | str]) -> List[str]:
    """Normalize permissions into a deterministic allow-list."""
    if raw_permissions is None:
        return []

    if isinstance(raw_permissions, str):
        raw_permissions = [raw_permissions]

    normalized: List[str] = []
    seen = set()
    for value in raw_permissions:
        if not value:
            continue
        permission = str(value).strip().lower()
        if permission in ALLOWED_PERMISSIONS and permission not in seen:
            normalized.append(permission)
            seen.add(permission)
    return normalized


def normalize_scope(raw_scope: Optional[str]) -> str:
    """Normalize scope values to the supported internal contract."""
    if not raw_scope:
        return "all"

    scope = str(raw_scope).strip().lower()
    scope_map = {
        "semantic": "all",
        "episodic": "all",
        "all": "all",
        "entire_memory": "all",
        "documents": "documents",
        "documents_only": "documents",
        "doc": "documents",
        "chat_history": "chat_history",
        "chat-history": "chat_history",
        "chat_history_only": "chat_history",
        "history": "chat_history",
    }
    return scope_map.get(scope, "all") if scope_map.get(scope, "all") in ALLOWED_SCOPES else "all"


def _is_missing_table_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "could not find the table" in message or "pgrst205" in message or "schema cache" in message


def _read_fallback_connections() -> List[Dict[str, Any]]:
    if not os.path.exists(FALLBACK_STORE_PATH):
        return []
    try:
        with open(FALLBACK_STORE_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                return payload.get("connections", [])
    except Exception:
        return []
    return []


def _write_fallback_connections(rows: List[Dict[str, Any]]) -> None:
    with open(FALLBACK_STORE_PATH, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)


def list_agent_connections(db: Any, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if not db:
        return []

    try:
        q = db.table("agent_connections").select("*")
        if agent_id:
            q = q.or_(f"source_agent_id.eq.{agent_id},target_agent_id.eq.{agent_id}")
        res = q.execute()
        rows = getattr(res, "data", None) or []
        if isinstance(rows, list):
            return rows
        if rows:
            return [rows]
        return []
    except Exception as exc:
        if _is_missing_table_error(exc):
            rows = _read_fallback_connections()
            if agent_id:
                return [row for row in rows if str(row.get("source_agent_id") or "") == agent_id or str(row.get("target_agent_id") or "") == agent_id]
            return rows
        raise


def create_agent_connection(db: Any, row: Dict[str, Any]) -> Dict[str, Any]:
    if not db:
        raise RuntimeError("database_unavailable")

    try:
        db.table("agent_connections").insert(row).execute()
        return row
    except Exception as exc:
        if _is_missing_table_error(exc):
            rows = _read_fallback_connections()
            rows.append(row)
            _write_fallback_connections(rows)
            return row
        raise


def update_agent_connection(db: Any, connection_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    if not db:
        raise RuntimeError("database_unavailable")

    try:
        db.table("agent_connections").update(updates).eq("id", connection_id).execute()
        return {**updates, "id": connection_id}
    except Exception as exc:
        if _is_missing_table_error(exc):
            rows = _read_fallback_connections()
            updated = None
            for row in rows:
                if row.get("id") == connection_id:
                    updated = {**row, **updates}
                    row.update(updated)
                    break
            if updated is None:
                updated = {"id": connection_id, **updates}
                rows.append(updated)
            _write_fallback_connections(rows)
            return updated
        raise


def evaluate_connection_access(
    db: Any,
    source_agent_id: str,
    target_agent_id: str,
    operation: str,
    requested_scope: Optional[str] = None,
) -> Tuple[bool, str]:
    """Return whether a source agent may access a target agent for the given operation."""
    if not source_agent_id or not target_agent_id:
        return False, "source_agent_id and target_agent_id are required"

    if source_agent_id == target_agent_id:
        return True, "same_agent"

    if not db:
        return False, "database_unavailable"

    try:
        rows = list_agent_connections(db, agent_id=source_agent_id)
        for row in rows:
            if str(row.get("source_agent_id") or "") != str(source_agent_id):
                continue
            if str(row.get("target_agent_id") or "") != str(target_agent_id):
                continue
            if str(row.get("status", "")).lower() != "approved":
                continue

            permissions = normalize_permissions(row.get("permissions") or [])
            if operation.lower() not in permissions:
                return False, f"Missing {operation.lower()} permission."

            scope = normalize_scope(row.get("scope") or "all")
            requested = normalize_scope(requested_scope or "all")
            if scope != "all" and requested != scope:
                return False, "Scope mismatch."

            return True, "approved"

        return False, "No approved connection found."
    except Exception as exc:  # pragma: no cover - defensive branch
        return False, str(exc)
