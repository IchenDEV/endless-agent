"""
中断系统 — 类似 CPU 中断控制器（PIC）。

所有外部事件（用户输入、定时器、信号等）统一封装为 Interrupt，
通过 asyncio.Queue 传递给主循环。支持多渠道上下文。
"""
import asyncio
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
    channel: str = "system"
    session_id: str = "default"
    priority: int = 0


class InterruptController:
    """中断控制器：管理中断队列，统一所有中断源。"""

    def __init__(self):
        self._queue: asyncio.Queue[Interrupt] = asyncio.Queue()

    async def wait(self) -> Interrupt:
        return await self._queue.get()

    async def emit(self, interrupt: Interrupt):
        await self._queue.put(interrupt)
