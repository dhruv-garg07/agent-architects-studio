import os
import json

def build_openapi_spec(static_dir):
    """
    Dynamically generate OpenAPI 3.0.3 specification object from the master static/index.json.
    Enforces explicit tag prioritization and operation ordering.
    """
    docs_path = os.path.join(static_dir, 'index.json')
    with open(docs_path, 'r', encoding='utf-8') as f:
        docs_data = json.load(f)
        
    openapi = {
        "openapi": "3.0.3",
        "info": {
            "title": "Agent Architects Studio API",
            "description": "OpenAPI specification dynamically generated from the master API schema, enabling centralized management of AI agents, documents, long-term memory, and multi-agent workflows.",
            "version": "1.0.0",
            "contact": {
                "name": "API Support",
                "url": "https://themanhattanproject.ai"
            }
        },
        "servers": [
            {
                "url": "https://themanhattanproject.ai",
                "description": "Production Server"
            },
            {
                "url": "http://localhost:1078",
                "description": "Local Development Server"
            }
        ],
        "tags": [
            {"name": "Agents", "description": "Core AI agent creation, lifecycle management, and chat inference endpoints."},
            {"name": "Documents", "description": "Vector knowledge base ingestion and semantic search management."},
            {"name": "Memory", "description": "Long-term structured memory lifecycle and hybrid retrieval units."},
            {"name": "Analytics & Stats", "description": "Volume, activity tracking, and real-time API usage analytics."},
            {"name": "Bulk Operations", "description": "High-volume batch insertion and memory pagination capabilities."},
            {"name": "Data Portability", "description": "Backup, migration, and AI-generated summary tools."},
            {"name": "API Test Examples", "description": "Connectivity verification and sample utility controllers."}
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Enter your API key as a Bearer token in the Authorization header. Example: Bearer sk-..."
                }
            }
        },
        "security": [{"BearerAuth": []}],
        "paths": {}
    }

    cat_priority = {
        "Agents": 1,
        "Documents": 2,
        "Memory": 3,
        "Analytics & Stats": 4,
        "Bulk Operations": 5,
        "Data Portability": 6,
    }
    sorted_categories = sorted(docs_data.get("categories", []), key=lambda c: cat_priority.get(c.get("name"), 99))

    ep_priority = {
        "/create_agent": 1,
        "/agent_chat": 2,
        "/list_agents": 3,
        "/get_agent": 4,
        "/update_agent": 5,
        "/disable_agent": 6,
        "/enable_agent": 7,
        "/delete_agent": 8,
        "/add_document": 10,
        "/search_documents": 11,
        "/create_memory": 20,
        "/add_memory": 21,
        "/get_context": 22,
        "/read_memory": 23,
    }

    for category in sorted_categories:
        cat_name = category.get("name", "General")
        sorted_endpoints = sorted(category.get("endpoints", []), key=lambda ep: ep_priority.get(ep.get("path"), 99))
        for ep in sorted_endpoints:
            path = ep.get("path")
            if not path or path.startswith("mcp://"):
                continue
                
            method = ep.get("method", "GET").lower()
            if path not in openapi["paths"]:
                openapi["paths"][path] = {}
                
            operation = {
                "tags": [cat_name],
                "summary": ep.get("summary", ""),
                "description": ep.get("description", ""),
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "example": ep.get("response") if ep.get("response") is not None else {}
                                }
                            }
                        }
                    }
                }
            }
            
            # Retain rich static description properties via standard OpenAPI x- extensions
            if ep.get("when_to_use"):
                operation["x-when-to-use"] = ep.get("when_to_use")
            if ep.get("use_cases"):
                operation["x-use-cases"] = ep.get("use_cases")
            if ep.get("notes"):
                operation["x-notes"] = ep.get("notes")
                
            req = ep.get("request")
            if req and isinstance(req, dict):
                if method in ["post", "put", "patch"]:
                    # Map as Request Body
                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        k: {
                                            "type": "string" if isinstance(v, str) else "object" if isinstance(v, dict) else "array" if isinstance(v, list) else "boolean" if isinstance(v, bool) else "string",
                                            "example": v
                                        }
                                        for k, v in req.items()
                                    }
                                }
                            }
                        }
                    }
                else:
                    # Map as Query Parameters
                    operation["parameters"] = [
                        {
                            "name": k,
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "example": str(v) if v is not None else ""
                        }
                        for k, v in req.items()
                    ]
                    
            openapi["paths"][path][method] = operation
            
    return openapi
