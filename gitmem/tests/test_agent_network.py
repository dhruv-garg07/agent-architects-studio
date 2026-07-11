import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))

from gitmem.core.access.agent_network import (
    normalize_permissions,
    normalize_scope,
    evaluate_connection_access,
)


class FakeTable:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = []

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def execute(self):
        self.calls.append(("execute", [], {}))
        return type("Resp", (), {"data": list(self.rows)})()


class FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.table_name = None

    def table(self, name):
        self.table_name = name
        if name == "agent_connections":
            return FakeTable(self.rows)
        raise AssertionError(f"Unexpected table {name}")


def test_normalize_permissions_filters_invalid_values():
    assert normalize_permissions(["read", "WRITE", "delete", "random"]) == ["read", "write", "delete"]


def test_normalize_scope_defaults_to_all():
    assert normalize_scope("semantic") == "all"
    assert normalize_scope("documents") == "documents"


def test_evaluate_connection_access_requires_approved_state_and_permission():
    db = FakeDB([
        {
            "source_agent_id": "src",
            "target_agent_id": "dst",
            "status": "approved",
            "permissions": ["read"],
            "scope": "all",
        }
    ])

    allowed, reason = evaluate_connection_access(db, "src", "dst", "read", "all")
    assert allowed is True
    assert reason == "approved"

    denied, reason = evaluate_connection_access(db, "src", "dst", "write", "all")
    assert denied is False
    assert "permission" in reason.lower()


def test_missing_table_falls_back_to_file_store(tmp_path, monkeypatch):
    from gitmem.core.access import agent_network

    monkeypatch.setattr(agent_network, "FALLBACK_STORE_PATH", str(tmp_path / "connections.json"))

    class MissingTableDB:
        def table(self, name):
            raise Exception("Could not find the table 'public.agent_connections' in the schema cache")

    row = {
        "id": "conn-1",
        "source_agent_id": "src",
        "target_agent_id": "dst",
        "status": "pending",
        "permissions": ["read"],
        "scope": "all",
    }

    created = agent_network.create_agent_connection(MissingTableDB(), row)
    assert created["id"] == "conn-1"
    stored = agent_network.list_agent_connections(MissingTableDB())
    assert stored[0]["id"] == "conn-1"


def test_connection_request_approval_and_network_routes(monkeypatch):
    from flask import Flask
    from flask_login import LoginManager, UserMixin

    from gitmem.api import routes as gitmem_routes

    class RouteFakeTable:
        def __init__(self, storage=None):
            self.storage = storage or []
            self.name = None
            self.updates = None

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            if args and args[0] == "id":
                self.filter_id = args[1]
            return self

        def insert(self, row):
            self.storage.append(row)
            return self

        def update(self, updates):
            self.updates = updates
            return self

        def execute(self):
            if self.name == "agent_connections":
                if self.updates is not None and getattr(self, "filter_id", None) is not None:
                    for row in self.storage:
                        if row.get("id") == self.filter_id:
                            row.update(self.updates)
                            break
                    self.updates = None
                    self.filter_id = None
                return type("Resp", (), {"data": list(self.storage)})()
            if self.name == "gitmem_memories":
                return type("Resp", (), {"data": list(self.storage)})()
            if self.name == "api_agents":
                return type("Resp", (), {"data": list(self.storage)})()
            if self.name == "profiles":
                return type("Resp", (), {"data": list(self.storage)})()
            return type("Resp", (), {"data": []})()

    class RouteFakeDB:
        def __init__(self):
            self.agent_rows = [
                {"agent_id": "src-agent", "user_id": "user-1", "agent_name": "Source", "agent_slug": "source"},
                {"agent_id": "dst-agent", "user_id": "user-1", "agent_name": "Target", "agent_slug": "target"},
            ]
            self.connection_rows = []
            self.memory_rows = []

        def table(self, name):
            table = RouteFakeTable()
            table.name = name
            if name == "api_agents":
                table.storage = self.agent_rows
                return table
            if name == "agent_connections":
                table.storage = self.connection_rows
                return table
            if name == "gitmem_memories":
                table.storage = self.memory_rows
                return table
            if name == "profiles":
                table.storage = [{"id": "user-1", "email": "user@example.com"}]
                return table
            raise AssertionError(f"Unexpected table {name}")

    class DummyUser(UserMixin):
        def __init__(self, user_id):
            self.id = user_id

        def get_id(self):
            return self.id

    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def load_user(user_id):
        return DummyUser(user_id)

    app.register_blueprint(gitmem_routes.gitmem_bp)

    fake_db = RouteFakeDB()
    monkeypatch.setattr(gitmem_routes, "_db", lambda: fake_db)

    class DummyRetrievalPipeline:
        def retrieve(self, **kwargs):
            return {"ok": True, "items": []}

    stub_module = types.SimpleNamespace(RetrievalPipeline=DummyRetrievalPipeline)
    monkeypatch.setitem(sys.modules, "gitmem.core.retrieval.retrieval", stub_module)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_user_id"] = "user-1"
        sess["_fresh"] = True

    request_resp = client.post(
        "/gitmem/api/agents/src-agent/connections/request",
        json={"target_agent_id": "dst-agent", "permissions": ["read", "write"], "scope": "all"},
    )
    assert request_resp.status_code == 201
    connection = request_resp.get_json()["connection"]
    connection_id = connection["id"]

    approve_resp = client.put(
        f"/gitmem/api/agents/dst-agent/connections/{connection_id}",
        json={"status": "approved"},
    )
    assert approve_resp.status_code == 200

    pull_resp = client.post(
        "/gitmem/api/agents/src-agent/network/pull",
        json={"target_agent_id": "dst-agent", "query": "hello"},
    )
    assert pull_resp.status_code == 200

    push_resp = client.post(
        "/gitmem/api/agents/src-agent/network/push",
        json={"target_agent_id": "dst-agent", "memory": "cross-agent sync"},
    )
    assert push_resp.status_code == 200
