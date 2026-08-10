import asyncio
import sys

from mcp_client import MCPClient


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
