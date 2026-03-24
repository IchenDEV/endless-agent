"""
中断系统 — 类似 CPU 中断控制器（PIC）。

所有外部事件（用户输入、定时器、信号等）统一封装为 Interrupt，
通过 asyncio.Queue 传递给主循环。
"""
import asyncio
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class InterruptType(Enum):
    USER_INPUT = auto()
    SIGNAL = auto()
    TIMER = auto()


@dataclass
class Interrupt:
    type: InterruptType
    payload: Any
    priority: int = 0


class InterruptController:
    """中断控制器：管理中断队列，提供注册中断源的能力。"""

    def __init__(self):
        self._queue: asyncio.Queue[Interrupt] = asyncio.Queue()
        self._running = False

    async def wait(self) -> Interrupt:
        return await self._queue.get()

    async def emit(self, interrupt: Interrupt):
        await self._queue.put(interrupt)

    async def start_stdin_listener(self):
        """在后台线程中监听 stdin，每行输入触发一个 USER_INPUT 中断。"""
        self._running = True
        loop = asyncio.get_running_loop()

        def _read_line():
            try:
                return sys.stdin.readline()
            except EOFError:
                return ""

        while self._running:
            line = await loop.run_in_executor(None, _read_line)
            if not line:
                await self.emit(Interrupt(type=InterruptType.SIGNAL, payload="EOF"))
                break
            text = line.rstrip("\n")
            if text:
                await self.emit(
                    Interrupt(type=InterruptType.USER_INPUT, payload=text)
                )

    def stop(self):
        self._running = False
