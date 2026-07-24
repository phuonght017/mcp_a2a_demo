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

Install with:
```bash
uv sync
```
