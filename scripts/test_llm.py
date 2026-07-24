#!/usr/bin/env python3
"""Test script to verify LLM connectivity before running MCP client."""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

# Ensure .env is loaded even if running from a different directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
load_dotenv(os.path.join(_project_root, ".env"))


def test_llm_connection():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")

    missing = []
    if not api_key:
        missing.append("LLM_API_KEY")
    if not base_url:
        missing.append("LLM_BASE_URL")
    if not model:
        missing.append("LLM_MODEL")

    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        print("   Please check your .env file.")
        sys.exit(1)

    print("🔑 API Key:", f"{api_key[:20]}..." if api_key and len(api_key) > 20 else api_key)
    print("🔗 Base URL:", base_url)
    print("🤖 Model:", model)
    print()

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'Hello from test script!'"}],
            max_tokens=512,
        )

        choice = response.choices[0]
        msg = choice.message
        content = msg.content

        print("✅ LLM connection successful!")
        print(f"🏁 Finish reason: {choice.finish_reason}")

        if content is None:
            print("⚠️  Response content is None")
            if msg.tool_calls:
                print(f"🛠️  Tool calls: {msg.tool_calls}")
            else:
                print("📝 No tool calls either — checking raw response dump:")
                print(response.model_dump_json(indent=2))
        else:
            print(f"📨 Response: {content}")

    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_llm_connection()