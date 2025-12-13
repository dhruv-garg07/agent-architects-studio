# Agent Collaboration Protocol v1.0

This document specifies the protocols and interfaces for AI agents operating within the Agent Architects Studio. It is intended for machine interpretation to enable inter-agent communication, collaboration, and task execution.

## 1. Prime Directive

The primary objective for all agents is to **receive, execute, and complete tasks dispatched by the system's central Task Dispatcher**. Collaboration is achieved by breaking down complex tasks into sub-tasks and passing structured data between agents via the Memory and Task systems.

## 2. Core Architecture

The system consists of three main components relevant to agent operation:

- **Task Dispatcher:** The central orchestrator that assigns tasks and manages their state.
- **Shared Memory (Octave_mem):** A multi-layered memory system for storing and retrieving information.
- **Communication Bus:** A direct messaging channel for inter-agent coordination.

## 3. Task Execution Protocol

Agents interact with the system through a task-based loop.

### 3.1. Task Schema

Tasks are received as a JSON object with the following structure:

```json
{
  "task_id": "string",
  "task_type": "string",
  "payload": {
    "objective": "string",
    "data": "any" 
  },
  "dependencies": ["task_id_1", "task_id_2"],
  "priority": "integer"
}
```

- **task_id**: A unique identifier for the task.
- **task_type**: The category of the task (e.g., `data_retrieval`, `text_generation`, `analysis`).
- **payload**: Contains the specific instructions and data needed to perform the task.
- **dependencies**: A list of `task_id`s that must be completed before this task can begin.
- **priority**: A number indicating the task's urgency.

### 3.2. Task Response Schema

Upon completion or failure, an agent MUST return a response to the Task Dispatcher with the following schema:

```json
{
  "task_id": "string",
  "status": "completed" | "failed" | "in_progress",
  "result": {
    "type": "string",
    "content": "any"
  },
  "error": {
    "code": "string",
    "message": "string"
  }
}
```
- **status**: The final state of the task.
- **result**: The output of a successful task.
- **error**: A description of why a task failed.

## 4. Agent Capabilities (API Reference)

Agents can invoke the following system functions via API calls.

### 4.1. Memory Interface

The Shared Memory is accessible via the `memory` API.

**Write to Memory**
- **Endpoint:** `POST /api/memory/write`
- **Description:** Stores or updates information in the RAG (long-term semantic) or SQL (short-term structured) memory.
- **Body:**
  ```json
  {
    "namespace": "string", // e.g., 'rag.research', 'sql.user_profiles'
    "key": "string",
    "value": "any"
  }
  ```

**Read from Memory**
- **Endpoint:** `POST /api/memory/read`
- **Description:** Performs a semantic search on the RAG memory or a key-based lookup.
- **Body:**
  ```json
  {
    "namespace": "string",
    "query": "string" // Semantic query for RAG, key for SQL
  }
  ```

### 4.2. Communication Interface

Direct inter-agent messaging is handled by the `communication` API.

**Send Message**
- **Endpoint:** `POST /api/chat`
- **Description:** Sends a direct message to another agent.
- **Body:**
  ```json
  {
    "recipient_agent_id": "string",
    "message_content": {
      "type": "coordination | data_exchange",
      "payload": "any"
    }
  }
  ```

## 5. Collaboration Workflow Example

**Objective:** "Generate a report on topic X."

1.  **Dispatch:** Task Dispatcher creates `task_A` ("Generate report on topic X") and assigns it to a `ManagerAgent`.

2.  **Decomposition:** `ManagerAgent` determines sub-tasks are needed. It instructs the Task Dispatcher to create:
    - `task_B` (`data_retrieval`): Assigned to `ResearchAgent`.
    - `task_C` (`text_generation`): Assigned to `WriterAgent`, with `dependencies: ["task_B"]`.

3.  **Execution (task_B):**
    - `ResearchAgent` receives `task_B`.
    - It calls `memory.read({ "namespace": "rag.research", "query": "topic X" })` to check for existing data.
    - It performs external data gathering.
    - It calls `memory.write({ "namespace": "rag.research", "key": "topic_X_sources", "value": [...] })` to store findings.
    - It reports `status: "completed"` for `task_B`.

4.  **Execution (task_C):**
    - Task Dispatcher detects `task_B` completion and assigns `task_C` to `WriterAgent`.
    - `WriterAgent` receives `task_C`.
    - It calls `memory.read({ "namespace": "rag.research", "query": "topic_X_sources" })` to retrieve the data.
    - It generates the report.
    - It reports `status: "completed"` for `task_C` with the report in the `result` field.

5.  **Completion:** `ManagerAgent` is notified of `task_C` completion and reports the final result for `task_A`.

This protocol ensures that agents can work together on complex, multi-step tasks in a structured and observable manner.