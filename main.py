"""
Agent 入口 — 启动永不停止的 Agent Loop。

Usage:
    export OPENAI_API_KEY="your-key"
    python main.py

可选环境变量:
    OPENAI_BASE_URL  — API 地址（默认 OpenAI 官方）
    AGENT_MODEL      — 模型名（默认 gpt-4o-mini）
"""
import asyncio
import signal
import sys


def main():
    from agent.loop import run_loop

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: loop.stop())

    try:
        loop.run_until_complete(run_loop())
    except (KeyboardInterrupt, SystemExit):
        print("\n\033[36m[Agent] 再见！\033[0m")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
