"""
核心事件循环 — 中断驱动的 Agent Loop。

永不停止。等待中断 → 处理 → 执行工具 → 反馈 → 等待下一个中断。
类似 CPU: while True → check interrupt → dispatch → idle。
"""
import asyncio
import sys

from agent.interrupt import Interrupt, InterruptController, InterruptType
from agent.message import MessageStore
from agent.tool import execute, format_result, parse_tool_calls, ToolCall
from agent import llm


MAX_TOOL_ROUNDS = 10


async def handle_user_input(text: str, store: MessageStore):
    """处理一次用户输入：调用 LLM，执行工具，循环直到没有 tool call。"""
    store.add_user(text)

    for _ in range(MAX_TOOL_ROUNDS):
        response = await llm.chat(store.to_messages())
        store.add_assistant(response)

        tool_calls = parse_tool_calls(response)
        if not tool_calls:
            break

        results = []
        for call in tool_calls:
            result = await execute(call)
            formatted = format_result(result)
            results.append(formatted)
            _print_tool_output(call, result)

        store.add_tool_result("\n\n".join(results))


def _print_tool_output(call: ToolCall, result):
    """将工具执行过程打印到终端，让用户能看到 Agent 在做什么。"""
    print(f"\033[90m$ {call.command}\033[0m", flush=True)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(f"\033[31m{result.stderr}\033[0m", end="", flush=True)
    if not result.stdout.endswith("\n") and not result.stderr.endswith("\n"):
        print(flush=True)


async def run_loop():
    """主循环：永不停止，中断驱动。"""
    controller = InterruptController()
    store = MessageStore()

    listener_task = asyncio.create_task(controller.start_stdin_listener())

    print("\033[36m[Agent] 已启动，等待输入... (Ctrl+C 退出)\033[0m", flush=True)
    print("\033[36m[Agent] 输入你的请求，按 Enter 发送。\033[0m", flush=True)

    try:
        while True:
            interrupt = await controller.wait()

            if interrupt.type == InterruptType.USER_INPUT:
                print(f"\033[33m[中断] 用户输入: {interrupt.payload}\033[0m", flush=True)
                try:
                    await handle_user_input(interrupt.payload, store)
                except Exception as e:
                    print(f"\033[31m[错误] {e}\033[0m", flush=True)
                print(f"\033[36m[Agent] 就绪，等待下一个中断...\033[0m", flush=True)

            elif interrupt.type == InterruptType.SIGNAL:
                if interrupt.payload == "EOF":
                    print("\033[36m[Agent] 检测到 EOF，退出。\033[0m", flush=True)
                    break

    except asyncio.CancelledError:
        pass
    finally:
        controller.stop()
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
