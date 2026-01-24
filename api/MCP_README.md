# Manhattan Memory MCP Server

> 🧠 **AI-powered memory management** for Claude, Cursor, and other AI coding agents.
> 
> **No setup required!** Use our hosted API - just download one file and add your API key.

---

## 🚀 Quick Start (2 Minutes)

### Option 1: Use Hosted API (Recommended)

**No repository clone needed!** Just download one file and configure.

#### Step 1: Download the MCP Client

```bash
# Download the single-file MCP client
curl -O https://raw.githubusercontent.com/your-username/agent-architects-studio/main/api/mcp_memory_client.py

# Or with wget
wget https://raw.githubusercontent.com/your-username/agent-architects-studio/main/api/mcp_memory_client.py
```

Or simply copy `mcp_memory_client.py` from this repo.

#### Step 2: Install Dependencies (2 packages)

```bash
pip install mcp httpx
```

#### Step 3: Get Your API Key

1. Visit [Agent Architects Studio](https://agent-architects-studio.onrender.com)
2. Sign up / Log in
3. Go to Settings → API Keys
4. Create a new key

#### Step 4: Configure Claude Desktop

Add to your Claude Desktop config file:

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["C:/path/to/mcp_memory_client.py"],
      "env": {
        "MANHATTAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**macOS** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python3",
      "args": ["/path/to/mcp_memory_client.py"],
      "env": {
        "MANHATTAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Linux** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python3",
      "args": ["/path/to/mcp_memory_client.py"],
      "env": {
        "MANHATTAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

#### Step 5: Restart Claude Desktop

That's it! 🎉

---

### Option 2: Self-Hosted (Advanced)

Clone the full repository and run your own server. See [SELF_HOSTED_SETUP.md](SELF_HOSTED_SETUP.md).

---

## 🔌 Integration Guides

### Claude Desktop
See Quick Start above.

### VS Code (GitHub Copilot)

1. **Install the MCP Extension**
   - Install the "MCP Server" extension for VS Code if available, or use the "MCP: Add Server" command from the Command Palette (`Cmd+Shift+P`).

2. **Configure via `mcp.json`**
   - Run **"MCP: Open User Configuration"** from Command Palette to open your `mcp.json`.
   - Add the server configuration:

```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["${workspaceFolder}/api/mcp_memory_client.py"],
      "env": {
        "MANHATTAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Cursor IDE

Add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_memory_client.py"],
      "env": {
        "MANHATTAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Windsurf IDE

Add to `~/.windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_memory_client.py"],
      "env": {
        "MANHATTAN_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Continue.dev

Add to `~/.continue/config.json`:
```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "python",
          "args": ["/absolute/path/to/mcp_memory_client.py"],
          "env": {
            "MANHATTAN_API_KEY": "your-api-key-here"
          }
        }
      }
    ]
  }
}
```

---

## 🛠️ Available Tools

Once configured, ask your AI assistant to use these tools.

### 🧠 Memory Operations
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `create_memory` | Initialize memory system for an agent | "Create a memory system for agent 'my-assistant'" |
| `process_raw_dialogues` | Extract memories from conversations | "Process this dialogue: Alice said 'Meeting at 2pm'" |
| `add_memory_direct` | Add structured memory (no AI) | "Add fact: Project deadline is Jan 30" |
| `search_memory` | Search memories | "Search 'my-assistant' for 'deadline'" |
| `get_context_answer` | Q&A with memory | "When is the deadline?" |
| `update_memory_entry` | Update existing memory | "Update memory XYZ with new deadline" |
| `delete_memory_entries` | Delete memories | "Delete memory entry XYZ" |
| `chat_with_agent` | Chat with agent context | "Chat with 'my-assistant': What do you recall?" |

### 🤖 Agent Management
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `create_agent` | Create a new agent | "Create agent 'research-bot'" |
| `list_agents` | List your agents | "List my agents" |
| `get_agent` | Get agent details | "Get details for 'research-bot'" |
| `update_agent` | Update agent config | "Update 'research-bot' description" |
| `disable_agent` | Disable an agent | "Disable 'research-bot'" |
| `enable_agent` | Enable a disabled agent | "Enable 'research-bot'" |
| `delete_agent` | Permanently delete agent | "Delete agent 'research-bot'" |

### 📊 Professional Tools
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `agent_stats` | Get usage statistics | "Show stats for 'research-bot'" |
| `list_memories` | List all memories (paginated) | "List all memories for 'research-bot'" |
| `bulk_add_memory` | Bulk import memories | "Import these 50 facts..." |
| `export_memories` | Export full backup | "Export all memories for 'research-bot'" |

---

## 💬 Usage Examples

### Create an agent memory

> **You:** "Create a memory system for agent 'project-helper'"
> 
> **Claude:** I'll create a memory system for your agent using the `create_memory` tool...

### Store important information

> **You:** "Add to 'project-helper' memory: The client deadline is February 15, 2025. The project budget is $50,000. Key stakeholders are John and Sarah."
> 
> **Claude:** I'll add these facts using `add_memory_direct`...

### Recall information later

> **You:** "Ask 'project-helper': What's the project budget?"
> 
> **Claude:** Using `get_context_answer`... The project budget is $50,000.

### Search memories

> **You:** "Search 'project-helper' for anything about deadlines"
> 
> **Claude:** Using `search_memory`... Found 1 result: "The client deadline is February 15, 2025"

---

## 🔐 Security & Privacy

- **Your data is isolated**: Each agent has its own private memory space
- **API key authentication**: All requests require a valid API key
- **Encrypted transmission**: All API calls use HTTPS
- **No data sharing**: Your memories are never used to train models or shared with others

---

## 🌐 API Endpoints

The MCP client connects to our hosted API at:

```
https://www.themanhattanproject.ai
```

Available endpoints (for direct API usage):
- `POST /create_memory` - Initialize memory system
- `POST /process_raw` - Process dialogues via LLM
- `POST /add_memory` - Direct memory save
- `POST /read_memory` - Hybrid search retrieval
- `POST /get_context` - Q&A with memory
- `POST /update_memory` - Update memory entry
- `POST /delete_memory` - Delete memories
- `POST /agent_chat` - Chat with agent

---

## 🔧 Troubleshooting

### "API key not configured"

Make sure `MANHATTAN_API_KEY` is set in your MCP config's `env` section.

### "Connection refused" or timeout

1. Check your internet connection
2. Verify the API is up: https://agent-architects-studio.onrender.com/ping
3. Note: First request may be slow (server cold start on Render free tier)

### "mcp module not found"

```bash
pip install mcp httpx
```

### Claude doesn't show memory tools

1. Verify config file path is correct for your OS
2. Check the Python path in your config
3. Restart Claude Desktop after config changes

---

## 📁 Files

| File | Description |
|------|-------------|
| `mcp_memory_client.py` | **Standalone** MCP client - all you need! |
| `mcp_memory_server.py` | Full server (for self-hosting) |
| `claude_desktop_config.json` | Config template |
| `setup_mcp.py` | Setup script (for self-hosting) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Your AI Coding Agent                     │
│     (Claude Desktop / Cursor / Windsurf / etc.)         │
└─────────────────────────┬───────────────────────────────┘
                          │ MCP Protocol (stdio)
                          ▼
┌─────────────────────────────────────────────────────────┐
│              mcp_memory_client.py                       │
│          (Lightweight - just HTTP calls)                │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────┐
│         Agent Architects Studio API                     │
│        (Hosted on Render.com)                           │
│   ┌──────────────────────────────────────────────┐      │
│   │  SimpleMem System    │    ChromaDB Vector    │      │
│   │  (AI Processing)     │    Store (Memory)     │      │
│   └──────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Issues and PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📞 Support

- **GitHub Issues**: [Report a bug](https://github.com/your-username/agent-architects-studio/issues)
- **Discord**: [Join our community](https://discord.gg/your-server)
- **Email**: support@agent-architects.studio

---

<p align="center">
  Made with ❤️ by <a href="https://agent-architects.studio">Agent Architects Studio</a>
</p>
