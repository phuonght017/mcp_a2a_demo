import asyncio
import json
import sys

import httpx

A2A_SERVER = "http://localhost:8000"


async def discover_agent(agent_id: str):
    """Lấy Agent Card để khám phá khả năng của Agent."""
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{A2A_SERVER}/agents/{agent_id}/agent.json")
        r.raise_for_status()
        return r.json()


async def send_task(agent_id: str, text: str):
    """Gửi một Task tới Agent thông qua A2A /tasks/send."""
    task_payload = {
        "id": "task-001",
        "sessionId": "session-001",
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": text}],
        },
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{A2A_SERVER}/agents/{agent_id}/tasks/send",
            json=task_payload,
        )
        r.raise_for_status()
        return r.json()


async def main():
    if len(sys.argv) < 3:
        print("Cách dùng: python a2a_client.py <agent_id> '<message>'")
        print("Ví dụ: python a2a_client.py direct-agent 'Giới thiệu về kiến trúc MCP + A2A'")
        print("Ví dụ: python a2a_client.py mcp-agent 'Tính 1+2 và kiểm tra trạng thái hệ thống'")
        sys.exit(1)

    agent_id = sys.argv[1]
    message = sys.argv[2]

    print(f"🔍 Khám phá Agent Card: {agent_id}")
    try:
        card = await discover_agent(agent_id)
        print(json.dumps(card, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Lỗi khám phá agent: {e}")
        return

    print(f"\n📤 Gửi task tới [{agent_id}]: {message}")
    try:
        result = await send_task(agent_id, message)
        print("📥 Phản hồi từ Agent:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Lỗi gửi task: {e}")


if __name__ == "__main__":
    asyncio.run(main())
