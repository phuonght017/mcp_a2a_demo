# mcp_a2a_demo

A demo project to learn how to build a basic multi-agent system using A2A and MCP.

---

## A. MCP Server and Client

### Overview

This project demonstrates a basic MCP setup with a **Server** exposing reusable tools/resources and a **Client** that connects to the server via STDIO and orchestrates tool calls using an OpenAI-compatible LLM.

### MCP Server (`server.py`)

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk). Exposes:

| Type | Name | Description |
|------|------|-------------|
| `tool` | `add_numbers` | Returns the sum of two floats |
| `tool` | `get_system_status` | Returns a mock system status string |
| `resource` | `config://app-settings` | Returns JSON config for the app |
| `prompt` | `system_audit_prompt` | Pre-built prompt to audit system status |

Run the server directly (STDIO transport):
```bash
uv run server.py
```

### MCP Client (`client.py`)

Connects to a server via STDIO, lists available tools, and drives a chat loop using an LLM with function-calling support.

How it works:
1. Spawns the server script as a subprocess over STDIO
2. Lists tools from the server and converts them to OpenAI function schemas
3. Sends the user query to the LLM together with the tool definitions
4. If the LLM requests a tool call, executes it on the MCP Server and feeds the result back
5. Repeats until the LLM returns a final answer

Run the client:
```bash
uv run client.py server.py
```

### Environment Setup

Create a `.env` file in the project root (copied from `.env.example`):

```bash
cp .env.example .env
```

Required variables:
- `LLM_API_KEY` — API key for the OpenAI-compatible endpoint
- `LLM_BASE_URL` — Base URL of the LLM gateway (e.g., `https://.../v1`)
- `LLM_MODEL` — Model name to use (e.g., `v_glm46`)

### Test LLM Connection

Before running the full client, verify the LLM endpoint is reachable:

```bash
uv run scripts/test_llm.py
```

This validates your `.env` config and sends a simple completion to confirm connectivity.

### Dependencies

Managed via `uv` / `pyproject.toml`:
- `mcp`
- `openai`
- `python-dotenv`
- `fastapi`
- `uvicorn`
- `httpx`

Install with:
```bash
uv sync
```

---

## B. A2A Server and Client

### Architecture Overview

```
┌─────────────┐      A2A Protocol       ┌─────────────────────────────┐
│  A2A Client  │  ───────────────────>  │        A2A Server            │
│ (a2a_client) │     HTTP/JSON          │      (a2a_server.py)          │
└─────────────┘                        │                             │
                                      │  ┌─────────────┐  ┌────────┐ │
                                      │  │ direct-agent │  │mcp-agent│ │
                                      │  │  (LLM only)  │  │(MCP    │ │
                                      │  └─────────────┘  │ + LLM)  │ │
                                      │                   └────┬───┘ │
                                      │                        │     │
                                      │                   MCP Client │
                                      │                        │     │
                                      │                   MCP Server │
                                      │                   (server.py)│
                                      └─────────────────────────────┘
```

### A2A Server (`a2a_server.py`)

FastAPI server implementing simplified Google A2A protocol.

| Agent | Description | Endpoint |
|-------|-------------|----------|
| `direct-agent` | Xử lý trực tiếp qua LLM, không dùng MCP | `/agents/direct-agent` |
| `mcp-agent` | Kết nối tới MCP Server (`server.py`) qua STDIO để gọi tools | `/agents/mcp-agent` |

Endpoints:
- `GET /agents/{agent_id}/agent.json` — Agent Card (metadata)
- `POST /agents/{agent_id}/tasks/send` — Gửi task và nhận kết quả

Run:
```bash
uv run a2a_server.py
```
Server listens on `http://localhost:8000`.

### A2A Client (`a2a_client.py`)

Client khám phá Agent Card và gửi task.

Usage:
```bash
uv run a2a_client.py <agent_id> "<message>"
```

Ví dụ:
```bash
# Gửi tới direct-agent
uv run a2a_client.py direct-agent "Giới thiệu về kiến trúc MCP và A2A"

# Gửi tới mcp-agent (yêu cầu LLM gọi tool)
uv run a2a_client.py mcp-agent "Tính tổng 5 và 10, sau đó kiểm tra trạng thái hệ thống"
```

### Run the Full Demo

1. **Start A2A Server**:
   ```bash
   uv run a2a_server.py
   ```
   
2. **In another terminal, run A2A Client**:
   ```bash
   uv run a2a_client.py direct-agent 'Chào bạn'
   uv run a2a_client.py mcp-agent 'Tính 2+3 và lấy trạng thái hệ thống'
   ```

3. **(Optional) Run original MCP Client directly**:
   ```bash
   uv run client.py server.py
   ```
