# Manhattan Memory MCP Server

> 🧠 **Model Context Protocol (MCP) Server** for AI-powered memory management with ChromaDB vector storage.

This MCP server enables **Claude Desktop**, **Claude Code (Antigravity)**, **Cursor**, **Windsurf**, and other AI coding agents to interact with your agent memory system through natural language.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **pip** or **uv** package manager
- Valid **ChromaDB** credentials (see Environment Setup)

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/agent-architects-studio.git
cd agent-architects-studio

# Install Python dependencies
pip install mcp python-dotenv httpx chromadb

# Or with uv
uv add mcp python-dotenv httpx chromadb
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# ChromaDB Configuration
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_tenant
CHROMA_DATABASE_CHAT_HISTORY=your_database_name

# Embedding Configuration
REMOTE_EMBEDDING_URL=https://your-embedding-service.com/embed
REMOTE_EMBEDDING_DIMENSION=768

# Optional: OpenAI for LLM processing
OPENAI_API_KEY=sk-your-openai-key
```

### 3. Test the Server

```bash
# From project root
python api/mcp_memory_server.py

# Expected output:
# Starting Manhattan Memory MCP Server...
# Tools available: create_memory, process_raw_dialogues, add_memory_direct...
# Running on stdio transport...
```

---

## 🔌 Integration Guide

### Claude Desktop

**Config location:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Add this configuration:**

```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": [
        "/absolute/path/to/agent-architects-studio/api/mcp_memory_server.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/agent-architects-studio"
      }
    }
  }
}
```

> ⚠️ **Important:** Replace `/absolute/path/to/` with your actual installation path.

**Windows Example:**
```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": [
        "C:/Projects/agent-architects-studio/api/mcp_memory_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:/Projects/agent-architects-studio"
      }
    }
  }
}
```

---

### Claude Code (Antigravity) / VS Code with Claude Extension

For **Claude Code** (the AI coding agent in VS Code), add the MCP server to your workspace settings:

**Option 1: Workspace Settings (`.vscode/settings.json`)**

```json
{
  "claude.mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["${workspaceFolder}/api/mcp_memory_server.py"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  }
}
```

**Option 2: Add to `.gemini/settings.json`** (for Antigravity integration)

Create or update `.gemini/settings.json` in your project root:

```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["api/mcp_memory_server.py"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  }
}
```

---

### Cursor IDE

**Config location:** `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["/path/to/agent-architects-studio/api/mcp_memory_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/agent-architects-studio"
      }
    }
  }
}
```

---

### Windsurf IDE

**Config location:** `~/.windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["/path/to/agent-architects-studio/api/mcp_memory_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/agent-architects-studio"
      }
    }
  }
}
```

---

### Continue.dev (VS Code Extension)

Add to your `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "python",
          "args": ["/path/to/agent-architects-studio/api/mcp_memory_server.py"],
          "env": {
            "PYTHONPATH": "/path/to/agent-architects-studio"
          }
        }
      }
    ]
  }
}
```

---

### Generic MCP Client (Programmatic)

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["api/mcp_memory_server.py"],
        env={"PYTHONPATH": "/path/to/agent-architects-studio"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])
            
            # Call a tool
            result = await session.call_tool(
                "create_memory",
                arguments={"agent_id": "my-agent", "clear_db": False}
            )
            print("Result:", result)

asyncio.run(main())
```

---

## 🛠️ Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_memory` | Initialize memory system for an agent | `agent_id`, `clear_db` |
| `process_raw_dialogues` | Process dialogues through LLM to extract memories | `agent_id`, `dialogues[]` |
| `add_memory_direct` | Add pre-structured memories (no LLM) | `agent_id`, `memories[]` |
| `search_memory` | Hybrid search (semantic + keyword) | `agent_id`, `query`, `top_k` |
| `get_context_answer` | Q&A with memory context | `agent_id`, `question` |
| `update_memory_entry` | Update existing memory | `agent_id`, `entry_id`, `updates` |
| `delete_memory_entries` | Delete memories by ID | `agent_id`, `entry_ids[]` |
| `list_all_memories` | List all memories for agent | `agent_id`, `limit` |

---

## 📝 Usage Examples

### With Claude Desktop

Once configured, simply ask Claude:

```
"Create a memory system for agent 'customer-support'"

"Process these dialogues for agent 'customer-support':
- User: I need help with my order #12345
- Agent: I'll look that up for you. What's the issue?"

"Search memories for 'customer-support' about order issues"

"For agent 'customer-support', answer: What was the user's order number?"
```

### With Claude Code (Antigravity)

In your coding session:

```
"Create a memory for this agent to remember our conversation context"

"Add to the agent's memory: We discussed implementing a REST API with Flask"

"What do you remember about our previous discussions on APIs?"
```

---

## 📂 Memory Entry Schema

```json
{
  "entry_id": "uuid-string",
  "lossless_restatement": "Self-contained fact: Alice scheduled a meeting with Bob at Starbucks on January 22, 2025 at 2pm",
  "keywords": ["meeting", "Starbucks", "Alice", "Bob", "schedule"],
  "timestamp": "2025-01-22T14:00:00",
  "location": "Starbucks, NYC",
  "persons": ["Alice", "Bob"],
  "entities": ["Order #12345", "Project Alpha"],
  "topic": "meeting scheduling"
}
```

---

## 🔧 Troubleshooting

### Server won't start

```bash
# Check Python version
python --version  # Should be 3.11+

# Verify MCP is installed
pip show mcp

# Check environment variables
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('CHROMA_API_KEY'))"
```

### Claude can't find the server

1. **Check absolute paths** - Relative paths don't work in MCP configs
2. **Verify Python is in PATH** - Run `where python` (Windows) or `which python` (Unix)
3. **Check Claude logs** - Look for MCP connection errors in Claude Desktop logs

### Import errors

```bash
# Install all dependencies
pip install mcp python-dotenv httpx chromadb openai pydantic

# Or from requirements.txt
pip install -r requirements.txt
```

### Permission errors (Windows)

Run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Coding Agent                          │
│         (Claude Desktop / Claude Code / Cursor)             │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol (stdio)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Manhattan Memory MCP Server                    │
│                  (mcp_memory_server.py)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ create_     │  │ search_     │  │ get_context │         │
│  │ memory      │  │ memory      │  │ _answer     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    SimpleMem System                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Memory      │  │ Hybrid      │  │ Answer      │         │
│  │ Builder     │  │ Retriever   │  │ Generator   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                   ChromaDB Vector Store                     │
│           (Cloud-hosted with remote embeddings)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/awesome-feature`
3. Commit changes: `git commit -m 'Add awesome feature'`
4. Push to branch: `git push origin feature/awesome-feature`
5. Open a Pull Request

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/agent-architects-studio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/agent-architects-studio/discussions)

---

Made with ❤️ by Agent Architects Studio
