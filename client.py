import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Tải cấu hình từ file .env
load_dotenv()

# Model công ty host qua endpoint OpenAI-compatible
MODEL_NAME = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "v_glm46"))


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # base_url trỏ tới gateway nội bộ của công ty (OpenAI-compatible)
        self.client = OpenAI(
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )

    async def connect_to_server(self, server_script_path: str):
        """Kết nối tới MCP Server chạy bằng Python qua giao thức STDIO"""
        python_executable = sys.executable

        server_params = StdioServerParameters(
            command=python_executable,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = [tool.name for tool in response.tools]
        print(f"\n✅ Đã kết nối thành công tới MCP Server!")
        print(f"🛠️  Danh sách Tools có sẵn: {tools}\n")

    def _to_openai_tools(self, mcp_tools) -> list:
        """Chuyển tool schema của MCP sang định dạng function-calling của OpenAI-compatible API"""
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
        """Xử lý yêu cầu của người dùng thông qua model công ty + MCP Tools"""
        messages = [{"role": "user", "content": query}]

        # 1. Lấy danh sách tools từ Server, convert sang format OpenAI-compatible
        tools_response = await self.session.list_tools()
        available_tools = self._to_openai_tools(tools_response.tools)

        # 2. Gửi request đầu tiên tới model
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=5000,
            messages=messages,
            tools=available_tools,
        )

        final_text = []

        # Lặp cho tới khi model không còn yêu cầu gọi tool nữa
        while True:
            choice = response.choices[0]
            msg = choice.message

            if msg.content:
                final_text.append(msg.content)

            # Không có tool call -> đây là câu trả lời cuối cùng
            if not msg.tool_calls:
                break

            # 3. Đưa message của assistant (kèm tool_calls) vào lịch sử hội thoại
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

            # 4. Thực thi từng tool call trên MCP Server
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_args = {}

                print(f"🤖 Model quyết định gọi Tool: [{tool_name}] với tham số: {tool_args}")

                result = await self.session.call_tool(tool_name, tool_args)
                result_text = result.content[0].text if result.content else ""
                print(f"⚙️ Phản hồi từ Server: {result_text}")

                # 5. Gửi kết quả tool về lại cho model (role="tool")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

            # Gọi lại model với kết quả tool để tổng hợp câu trả lời tiếp theo
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                max_tokens=1000,
                messages=messages,
                tools=available_tools,
            )

        return "\n".join(final_text)

    async def chat_loop(self):
        """Vòng lặp Chat tương tác trực tiếp trên Terminal"""
        print("💬 Bắt đầu phiên trò chuyện (Gõ 'quit' để thoát)")
        while True:
            try:
                query = input("\nBạn: ").strip()
                if not query:
                    continue
                if query.lower() in ['quit', 'exit']:
                    break

                response = await self.process_query(query)
                print(f"\nModel: {response}")
            except Exception as e:
                print(f"\n❌ Lỗi: {str(e)}")

    async def cleanup(self):
        """Đóng kết nối an toàn"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Cú pháp: uv run client.py <đường_dẫn_file_server.py>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())