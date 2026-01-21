# Manhattan Memory MCP Server

This MCP (Model Context Protocol) server exposes the Memory CRUD functionality to Claude and other MCP-compatible clients.

## Overview

The MCP server provides tools for:
- **create_memory** - Initialize memory system for an agent (ChromaDB collection)
- **process_raw_dialogues** - Process dialogues through LLM → extract memory entries
- **add_memory_direct** - Direct memory save without LLM processing
- **search_memory** - Hybrid search retrieval (semantic + keyword + structured)
- **get_context_answer** - Full Q&A using memory context
- **update_memory_entry** - Update existing memory entries
- **delete_memory_entries** - Delete memory entries
- **list_all_memories** - List all memories for an agent

## Installation

### 1. Install the MCP SDK

```bash
pip install mcp
# Or with uv:
uv add mcp
```

### 2. Verify Dependencies

Make sure you have all required dependencies:
```bash
pip install python-dotenv httpx
```

## Running the Server

### Standalone (for testing)
```bash
cd c:\Desktop\python_workspace_311\PdM-main\PdM-main\agent-architects-studio
python api/mcp_memory_server.py
```

### With uv
```bash
uv run api/mcp_memory_server.py
```

## Connecting to Claude Desktop

### 1. Locate the Claude Desktop config file

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### 2. Add the MCP Server Configuration

Copy the contents of `claude_desktop_config.json` to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "manhattan-memory": {
      "command": "python",
      "args": [
        "c:/Desktop/python_workspace_311/PdM-main/PdM-main/agent-architects-studio/api/mcp_memory_server.py"
      ],
      "env": {
        "PYTHONPATH": "c:/Desktop/python_workspace_311/PdM-main/PdM-main/agent-architects-studio"
      }
    }
  }
}
```

> **Note:** Update the paths to match your installation location.

### 3. Restart Claude Desktop

After updating the config, restart Claude Desktop to pick up the new MCP server.

## Testing the Connection

Once connected, you can ask Claude:

```
What MCP tools are available for memory management?
```

Claude should list the available memory tools.

### Example Tool Usage

**Create a memory system:**
```
Create a memory system for agent "my-test-agent"
```

**Add dialogues:**
```
Process these dialogues for agent "my-test-agent":
- Alice said "Let's meet at Starbucks tomorrow at 2pm"
- Bob replied "I'll bring the documents"
```

**Search memories:**
```
Search the memories for "my-test-agent" with query "When is the meeting?"
```

**Get a contextual answer:**
```
For agent "my-test-agent", answer: "What did Alice and Bob discuss?"
```

## MCP Resources

The server also exposes resources:

- `memory://agents/list` - List all active agents with memory systems
- `memory://config/info` - Get server info and available tools

## Troubleshooting

### Server won't start
1. Check Python version (3.11+ recommended)
2. Verify MCP package is installed: `pip show mcp`
3. Check PYTHONPATH includes the project root

### Claude can't find the server
1. Verify the absolute path in `claude_desktop_config.json` is correct
2. Check Claude Desktop logs for errors
3. Make sure Python is in your system PATH

### Import errors
Make sure the project dependencies are installed:
```bash
pip install -r requirements.txt
```

## API Reference

### Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_memory` | Initialize memory system | `agent_id`, `clear_db` |
| `process_raw_dialogues` | Process dialogues via LLM | `agent_id`, `dialogues` |
| `add_memory_direct` | Direct memory save | `agent_id`, `memories` |
| `search_memory` | Hybrid search | `agent_id`, `query`, `top_k`, `enable_reflection` |
| `get_context_answer` | Q&A with memory | `agent_id`, `question` |
| `update_memory_entry` | Update entry | `agent_id`, `entry_id`, `updates` |
| `delete_memory_entries` | Delete entries | `agent_id`, `entry_ids` |
| `list_all_memories` | List all memories | `agent_id`, `limit` |

### Memory Entry Schema

```json
{
  "lossless_restatement": "Self-contained fact statement",
  "keywords": ["keyword1", "keyword2"],
  "timestamp": "2025-01-22T14:00:00",
  "location": "Starbucks, NYC",
  "persons": ["Alice", "Bob"],
  "entities": ["Product X", "Company Y"],
  "topic": "meeting scheduling"
}
```

## License

Part of the Manhattan Project - Agent Architects Studio
