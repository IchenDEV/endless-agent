"""
核心事件循环 — 中断驱动的 Agent Loop。

永不停止。在终端收发消息。
等待中断 → 调用 LLM (function calling) → 执行 Skill → 反馈 → 等待。
"""
import asyncio
import json
from pathlib import Path

from agent.interrupt import InterruptController, InterruptType
from agent.message import MessageStore
from agent.prompt import system_message
from agent.scheduler import Scheduler
from agent.skill import SkillsProvider, TOOLS, handle_tool_call
from agent import llm


MAX_TOOL_ROUNDS = 10
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


async def run_loop():
    """主循环：永不停止，中断驱动，终端交互。"""
    provider = SkillsProvider(SKILLS_DIR)

    controller = InterruptController()
    scheduler = Scheduler(controller)
    store = MessageStore()
    store._system = system_message(provider.advertise_text())

    listener_task = asyncio.create_task(controller.start_stdin_listener())
    scheduler.start_all()

    _print_cyan("[Agent] 已启动，等待输入... (Ctrl+C 退出)")

    try:
        while True:
            interrupt = await controller.wait()

            if interrupt.type == InterruptType.USER_INPUT:
                _print_yellow(f"[中断] 用户输入")
                try:
                    await _handle_user(interrupt.payload, store, provider)
                except Exception as e:
                    _print_red(f"[错误] {e}")
                _print_cyan("[Agent] 就绪，等待下一个中断...")

            elif interrupt.type == InterruptType.TIMER:
                data = interrupt.payload
                prompt = data.get("data", "") if isinstance(data, dict) else str(data)
                if prompt:
                    try:
                        await _handle_user(prompt, store, provider)
                    except Exception as e:
                        _print_red(f"[定时任务错误] {e}")

            elif interrupt.type == InterruptType.SIGNAL:
                if interrupt.payload == "EOF":
                    _print_cyan("[Agent] 检测到 EOF，退出。")
                    break

    except asyncio.CancelledError:
        pass
    finally:
        scheduler.stop_all()
        controller.stop()
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass


async def _handle_user(text: str, store: MessageStore, provider: SkillsProvider):
    """处理一次输入：LLM → tool_calls → Skill 执行 → 循环。"""
    store.add_user(text)

    for _ in range(MAX_TOOL_ROUNDS):
        message = await llm.chat(store.to_messages(), tools=TOOLS)

        assistant_dict = _message_to_dict(message)
        store.add_assistant(assistant_dict)

        if not message.tool_calls:
            if message.content:
                print(message.content, flush=True)
            break

        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            cmd_display = args.get("command", args.get("name", tc.function.name))
            _print_dim(f"$ [{tc.function.name}] {cmd_display}")

            result = await handle_tool_call(provider, tc.function.name, tc.function.arguments)
            print(result, flush=True)

            store.add_tool_result(tc.id, result)


def _message_to_dict(msg) -> dict:
    """ChatCompletionMessage → dict，保留 tool_calls。"""
    d: dict = {"role": "assistant"}
    if msg.content:
        d["content"] = msg.content
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def _print_cyan(text: str):
    print(f"\033[36m{text}\033[0m", flush=True)

def _print_yellow(text: str):
    print(f"\033[33m{text}\033[0m", flush=True)

def _print_red(text: str):
    print(f"\033[31m{text}\033[0m", flush=True)

def _print_dim(text: str):
    print(f"\033[90m{text}\033[0m", flush=True)
