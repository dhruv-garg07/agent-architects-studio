# Exhibit A: Schedule of Deliverables
## Open-Source and Third-Party Components

The following table lists all open-source and third-party software components required for the operation of the core API service (`api/`) and the GitMem memory orchestrator (`gitmem/`).

| Component Name | Version | License | Manner of Use / Distribution |
| :--- | :--- | :--- | :--- |
| **Flask** | 3.1.0 | BSD-3-Clause | Core Backend Application Framework (`api/index.py`, `gitmem/api/routes.py`) |
| **Flask-Login** | 0.6.3 | MIT | User Authentication & Session Management (`gitmem/api/routes.py`) |
| **Flask-SocketIO** | 5.3.0 | MIT | Real-Time WebSocket Communication Layer (`gitmem/api/websocket_events.py`) |
| **Gunicorn** | 21.2.0 | MIT | WSGI HTTP Application Server for Production Deployment |
| **Gevent** | 23.9.0 | MIT | Asynchronous Coroutine Worker for Gunicorn Server |
| **Werkzeug** | 3.1.3 | BSD-3-Clause | WSGI Web Application Utilities & Security |
| **Jinja2** | 3.1.4 | BSD-3-Clause | Server-side Template Rendering Engine |
| **Pydantic** | 2.9.2 | MIT | Data Validation & Schema Serialization (`gitmem/core/models.py`) |
| **Supabase Python SDK** | 2.4.0 | MIT | Database & Workspace Storage Client (`gitmem/core/storage/supabase_connector.py`) |
| **OpenAI Python SDK** | Latest | Apache-2.0 | Vector Embeddings & LLM Integration (`gitmem/core/retrieval/embedder.py`) |
| **Tiktoken** | 0.12.0 | MIT | Fast Token Counting for LLM Context Windows (`gitmem/core/retrieval/token_packer.py`) |
| **ChromaDB** | 0.5.0 | Apache-2.0 | Vector Engine for Memory & Semantic Search (`gitmem/core/storage/vector_engine.py`) |
| **NumPy** | 2.2.6 | BSD-3-Clause | Mathematical Vector Operations (`gitmem/core/storage/vector_engine.py`) |
| **Model Context Protocol (MCP)** | Latest | MIT | Protocol SDK for Agent Context Sharing (`api/mcp_memory_server.py`) |
| **Requests** | 2.31.0 | Apache-2.0 | Synchronous HTTP API Client (`gitmem/sdk/client.py`) |
| **HTTPX** | 0.24.0 | BSD-3-Clause | Asynchronous HTTP Client (`api/mcp_memory_client.py`) |
| **Together AI SDK** | Latest | Apache-2.0 | LLM API Gateway Client (`LLM_calls/together_get_response.py`) |
| **Cryptography** | Latest | Apache-2.0 / BSD | API Key Hashing & Security Utilities (`api/key_utils.py`) |
| **python-dotenv** | 1.0.0 | BSD-3-Clause | Environment Variables Management |
| **Socket.IO Client** | 4.7.2 | MIT | Frontend Real-Time WebSocket Client (`gitmem/templates/hub_chat.html`) |
| **Vis Network** | Latest | Apache-2.0 / MIT | Interactive Knowledge Graph Visualizer (`gitmem/templates/hub_knowledge_studio.html`) |
| **Force Graph** | 1.43 | MIT | 2D/3D Agent Graph Rendering (`gitmem/templates/agent_dashboard.html`) |
| **Marked.js** | Latest | MIT | Client-side Markdown Rendering (`gitmem/templates/file_view.html`) |
| **Swagger UI** | 5.11.0 | Apache-2.0 | Interactive API Documentation Interface (`templates/swagger_ui.html`) |
| **Tailwind CSS CDN** | Latest | MIT | Utility Styling Framework (`templates/base.html`) |
| **Lucide Icons** | Latest | ISC | UI Vector Icon Set (`templates/base.html`) |
