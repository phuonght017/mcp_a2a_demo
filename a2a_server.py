import os
import sys
from typing import Literal, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

from mcp_client import MCPClient  # noqa: E402

# ------------------------------------------------------------
# Cấu hình
# ------------------------------------------------------------
MODEL_NAME = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "v_glm46"))
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "server.py")

llm_client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
)

# ------------------------------------------------------------
# A2A Data Models (đơn giản hóa từ Google A2A spec)
# ------------------------------------------------------------
class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Message(BaseModel):
    role: str
    parts: list[TextPart]


class Task(BaseModel):
    id: str
    sessionId: Optional[str] = None
    status: Literal["submitted", "working", "input-required", "completed", "canceled", "failed"] = "submitted"
    message: Optional[Message] = None
    artifacts: Optional[list[dict]] = None


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    capabilities: dict
    skills: list[dict]
    defaultInputModes: list[str]
    defaultOutputModes: list[str]


# ------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------
app = FastAPI(title="A2A Demo Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_agent_card(agent_id: str) -> Optional[AgentCard]:
    if agent_id == "direct-agent":
        return AgentCard(
            name="direct-agent",
            description="Agent xử lý trực tiếp thông qua LLM (không dùng MCP).",
            url="http://localhost:8000/agents/direct-agent",
            version="1.0.0",
            capabilities={"streaming": False, "pushNotifications": False},
            skills=[{"id": "chat", "name": "Trò chuyện trực tiếp với LLM"}],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        )
    if agent_id == "mcp-agent":
        return AgentCard(
            name="mcp-agent",
            description="Agent kết nối với MCP Server để sử dụng tools như add_numbers và get_system_status.",
            url="http://localhost:8000/agents/mcp-agent",
            version="1.0.0",
            capabilities={"streaming": False, "pushNotifications": False},
            skills=[{"id": "mcp-tools", "name": "Thực thi MCP Tools"}],
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        )
    return None


# ------------------------------------------------------------
# Agent Handlers
# ------------------------------------------------------------
async def handle_direct_agent(task: Task) -> Task:
    user_text = ""
    if task.message:
        for part in task.message.parts:
            if part.type == "text":
                user_text += part.text

    try:
        response = llm_client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=2000,
            messages=[{"role": "user", "content": user_text}],
        )
        reply = response.choices[0].message.content or "Không có phản hồi."
    except Exception as e:
        reply = f"Lỗi khi gọi LLM: {str(e)}"

    return Task(
        id=task.id,
        sessionId=task.sessionId,
        status="completed",
        message=task.message,
        artifacts=[{"parts": [{"type": "text", "text": reply}]}],
    )


async def handle_mcp_agent(task: Task) -> Task:
    user_text = ""
    if task.message:
        for part in task.message.parts:
            if part.type == "text":
                user_text += part.text

    client = MCPClient(server_script_path=MCP_SERVER_PATH)
    try:
        await client.connect_to_server(MCP_SERVER_PATH)
        result_text = await client.process_query(user_text)
    except Exception as e:
        result_text = f"Lỗi khi gọi MCP Agent: {str(e)}"
    finally:
        await client.cleanup()

    return Task(
        id=task.id,
        sessionId=task.sessionId,
        status="completed",
        message=task.message,
        artifacts=[{"parts": [{"type": "text", "text": result_text}]}],
    )


# ------------------------------------------------------------
# A2A Endpoints (tương thích Google A2A protocol)
# ------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "A2A Demo Server",
        "agents": ["/agents/direct-agent", "/agents/mcp-agent"],
    }


@app.get("/agents/{agent_id}/agent.json")
async def get_agent_card(agent_id: str):
    card = build_agent_card(agent_id)
    if not card:
        return {"error": "Agent not found"}
    return card


@app.post("/agents/{agent_id}/tasks/send")
async def send_task(agent_id: str, task: Task):
    if agent_id == "direct-agent":
        result = await handle_direct_agent(task)
    elif agent_id == "mcp-agent":
        result = await handle_mcp_agent(task)
    else:
        return {"error": "Agent not found"}
    return result


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
