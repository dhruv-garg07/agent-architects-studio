# MCP Memory Session Enforcement System

## Overview

This document describes the **mandatory session enforcement system** that ensures AI agents (like Claude, GitHub Copilot, etc.) **MUST** use the MCP memory system for all CRUD operations when a new chat window is opened.

## Key Features

### 1. Mandatory Agent ID Requirement
- If an AI agent doesn't have an `agent_id`, it **MUST** ask the user for one
- The system provides prompts and options for the user:
  - Use existing agent_id
  - Create a new agent
  - Use the default enterprise agent

### 2. Session Lifecycle Management
- **session_start**: Must be called at the beginning of every new conversation
- **session_end**: Should be called when conversation ends to sync all memories
- **pull_context**: Loads relevant memories at session start
- **push_memories**: Syncs pending memories to cloud storage

### 3. Automatic Context Loading
- When `session_start` is called, it automatically pulls relevant memories
- The agent receives formatted context to use in responses
- No excuses for lack of personalization!

## New MCP Tools

### Session Management Tools (MANDATORY)

| Tool | Description | When to Call |
|------|-------------|--------------|
| `check_session_status` | Check if session is initialized | **FIRST** at conversation start |
| `session_start` | Initialize session and load context | After checking status |
| `session_end` | End session and push all memories | When conversation ends |
| `pull_context` | Pull comprehensive context | At start or when needed |
| `push_memories` | Sync pending memories to cloud | Every 5-10 messages |
| `request_agent_id` | Get prompts to ask user for agent_id | When agent_id is missing |
| `get_startup_instructions` | Get mandatory startup protocol | At session start |

### Existing Memory Tools

| Tool | Description | When to Call |
|------|-------------|--------------|
| `search_memory` | Search for relevant memories | Before answering questions |
| `add_memory_direct` | Store new information | When user shares facts |
| `auto_remember` | Auto-extract facts from messages | After every user message |
| `get_context_answer` | Q&A with memory context | For comprehensive answers |

## Startup Protocol

AI agents MUST follow this protocol at the start of every new conversation:

```
1. Call check_session_status
   ↓
   If AGENT_ID_REQUIRED:
     → Call request_agent_id
     → ASK the user for their agent_id
     → Wait for user response
   ↓
2. Call session_start(agent_id)
   ↓
3. Review returned context
   ↓
4. Use context to personalize responses
```

## Example Workflow

### New Conversation Start

```python
# Step 1: Check session status (AI agent calls this automatically)
result = await check_session_status()

if result["status"] == "AGENT_ID_REQUIRED":
    # Step 2: Ask user for agent_id
    prompts = await request_agent_id()
    # AI agent uses prompts to ask user
    # User provides: "my-assistant" or existing ID

# Step 3: Start session with agent_id
session = await session_start(
    agent_id="my-assistant",
    auto_pull_context=True
)

# Step 4: Session returns context - use it!
context = session["context"]["memories"]
# AI now has personalized context for responses
```

### During Conversation

```python
# After each user message
await auto_remember(agent_id="my-assistant", user_message=user_input)

# Before responding to questions about past context
memories = await search_memory(agent_id="my-assistant", query="relevant query")

# When user shares new information
await add_memory_direct(
    agent_id="my-assistant",
    memories=[{
        "lossless_restatement": "User prefers Python over JavaScript",
        "keywords": ["preference", "python", "javascript"],
        "topic": "programming preferences"
    }]
)

# Every 5-10 messages
await push_memories(agent_id="my-assistant")
```

### Conversation End

```python
# When user says goodbye or conversation ends
await session_end(
    agent_id="my-assistant",
    conversation_summary="Discussed Python preferences and project setup",
    key_points=["Python preferred", "Working on React project"]
)
```

## Configuration

### MCP Settings (`.vscode/mcp_settings.json`)

```json
{
    "mcpServers": {
        "manhattan-memory": {
            "command": "python",
            "args": ["${workspaceFolder}/api/mcp_memory_client.py"],
            "env": {
                "PYTHONPATH": "${workspaceFolder}",
                "MANHATTAN_API_URL": "https://www.themanhattanproject.ai",
                "MANHATTAN_API_KEY": "your-api-key"
            }
        }
    }
}
```

### Default Agent ID

If no agent_id is provided, the system uses the enterprise default:
```
84aab1f8-3ea9-4c6a-aa3c-cd8eaa274a5e
```

However, agents are encouraged to ask users for personalized agent IDs for better experience.

## Benefits

1. **Guaranteed Context**: Agents always have relevant context loaded
2. **No Lost Information**: All memories are synced to cloud storage
3. **Personalized Responses**: Users get recognized and remembered
4. **Session Continuity**: Context persists across conversations
5. **Proactive Memory Building**: Agents actively build user profiles

## Enforcement Mechanism

The system enforces memory usage through:

1. **MCP Server Instructions**: Clear directives in the FastMCP instructions
2. **Session State Tracking**: Tracks whether session is properly initialized
3. **Tool Descriptions**: Emphatic language indicating mandatory usage
4. **Resources**: Behavioral instructions available as MCP resources
5. **Blocking Actions**: Session tools indicate blocking requirements

## Files

- `api/mcp_memory_client.py` - Main MCP server with session tools
- `api/mcp_session_enforcer.py` - Session enforcement module
- `SESSION_ENFORCEMENT.md` - This documentation

## Version

- **v3.0** - Session Enforced Edition
- Requires MCP SDK and httpx packages
