"""
Agent 入口 — 启动永不停止的 Agent Loop。

Usage:
    # CLI 模式（默认）
    python main.py

    # Web 模式（兼容 Vercel AI SDK）
    python main.py --web

    # 同时启动 CLI + Web
    python main.py --web --cli

环境变量:
    OPENAI_API_KEY   — 必需
    OPENAI_BASE_URL  — API 地址（可选）
    AGENT_MODEL      — 模型名（默认 gpt-4o-mini）
    WEB_PORT         — Web 端口（默认 3000）
"""
import argparse
import asyncio
import os
import signal

from agent.loop import AgentLoop
from agent.channels.cli import CLIChannel
from agent.channels.web import WebChannel


def parse_args():
    parser = argparse.ArgumentParser(description="Agent Loop")
    parser.add_argument("--web", action="store_true", help="启动 Web 渠道 (Vercel AI SDK 兼容)")
    parser.add_argument("--cli", action="store_true", help="启动 CLI 渠道")
    parser.add_argument("--port", type=int, default=int(os.environ.get("WEB_PORT", "3000")), help="Web 端口")
    return parser.parse_args()


async def run(args):
    agent = AgentLoop()

    if args.cli:
        agent.add_channel(CLIChannel(agent.controller))
    if args.web:
        agent.add_channel(WebChannel(agent.controller, port=args.port))

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    agent_task = asyncio.create_task(agent.start())

    await shutdown_event.wait()
    await agent.stop()
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass

    print("\n\033[36m[Agent] 再见！\033[0m")


def main():
    args = parse_args()
    if not args.web and not args.cli:
        args.cli = True

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
