import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

load_dotenv()

MODEL_NAME = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "v_glm46"))


class MCPClient:
    """Client kết nối tới MCP Server qua STDIO và tích hợp với LLM OpenAI-compatible."""

    def __init__(self, server_script_path: Optional[str] = None):
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )

    async def connect_to_server(self, server_script_path: str | None = None):
        """Kết nối tới MCP Server chạy bằng Python qua giao thức STDIO."""
        path = server_script_path or self.server_script_path
        if not path:
            raise ValueError("Cần cung cấp đường dẫn server script")

        python_executable = sys.executable
        server_params = StdioServerParameters(
            command=python_executable,
            args=[path],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = [tool.name for tool in response.tools]
        print(f"\n✅ Đã kết nối thành công tới MCP Server!")
        print(f"🛠️  Danh sách Tools có sẵn: {tools}\n")

    def _to_openai_tools(self, mcp_tools) -> list:
        """Chuyển tool schema của MCP sang định dạng function-calling của OpenAI-compatible API."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in mcp_tools
        ]

    async def process_query(self, query: str) -> str:
        """Xử lý yêu cầu của người dùng thông qua model công ty + MCP Tools."""
        messages = [{"role": "user", "content": query}]

        tools_response = await self.session.list_tools()
        available_tools = self._to_openai_tools(tools_response.tools)

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=5000,
            messages=messages,
            tools=available_tools,
        )

        final_text = []

        while True:
            choice = response.choices[0]
            msg = choice.message

            if msg.content:
                final_text.append(msg.content)

            if not msg.tool_calls:
                break

            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_args = {}

                print(f"🤖 Model quyết định gọi Tool: [{tool_name}] với tham số: {tool_args}")

                result = await self.session.call_tool(tool_name, tool_args)
                result_text = result.content[0].text if result.content else ""
                print(f"⚙️  Phản hồi từ Server: {result_text}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=1000,
                messages=messages,
                tools=available_tools,
            )

        return "\n".join(final_text)

    async def chat_loop(self):
        """Vòng lặp Chat tương tác trực tiếp trên Terminal."""
        print("💬 Bắt đầu phiên trò chuyện (Gõ 'quit' để thoát)")
        while True:
            try:
                query = input("\nBạn: ").strip()
                if not query:
                    continue
                if query.lower() in ["quit", "exit"]:
                    break

                response = await self.process_query(query)
                print(f"\nModel: {response}")
            except Exception as e:
                print(f"\n❌ Lỗi: {str(e)}")

    async def cleanup(self):
        """Đóng kết nối an toàn."""
        await self.exit_stack.aclose()
