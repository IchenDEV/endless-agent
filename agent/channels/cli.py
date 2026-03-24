"""
CLI 渠道 — stdin/stdout 交互。
"""
import asyncio
import sys

from agent.channels.base import Channel
from agent.interrupt import Interrupt, InterruptController, InterruptType


class CLIChannel(Channel):
    """通过 stdin 读取用户输入，通过 stdout 输出。"""

    def __init__(self, controller: InterruptController):
        self._controller = controller
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        return "cli"

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._listen())
        print("\033[36m[Agent] 已启动，等待输入... (Ctrl+C 退出)\033[0m", flush=True)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def send_text(self, session_id: str, text: str):
        print(text, flush=True)

    async def send_tool_output(self, session_id: str, tool_name: str, command: str, output: str):
        print(f"\033[90m$ {command}\033[0m", flush=True)
        if output:
            print(output, flush=True)

    async def _listen(self):
        loop = asyncio.get_running_loop()

        def _read_line():
            try:
                return sys.stdin.readline()
            except EOFError:
                return ""

        while self._running:
            line = await loop.run_in_executor(None, _read_line)
            if not line:
                await self._controller.emit(
                    Interrupt(type=InterruptType.SIGNAL, payload="EOF", channel="cli", session_id="cli")
                )
                break
            text = line.rstrip("\n")
            if text:
                await self._controller.emit(
                    Interrupt(
                        type=InterruptType.USER_INPUT,
                        payload=text,
                        channel="cli",
                        session_id="cli",
                    )
                )
