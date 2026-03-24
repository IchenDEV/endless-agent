"""
定时任务调度器 — 作为 TIMER 中断源。

支持 interval（固定间隔）和 cron（cron 表达式）两种模式。
所有定时事件统一通过 InterruptController 发射 TIMER 中断。
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Any

from agent.interrupt import Interrupt, InterruptController, InterruptType


@dataclass
class Job:
    name: str
    payload: Any
    interval: float | None = None
    cron: str | None = None
    enabled: bool = True


class Scheduler:
    """轻量定时调度器，每个 Job 一个 asyncio task。"""

    def __init__(self, controller: InterruptController):
        self._controller = controller
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def add(self, job: Job):
        self._jobs[job.name] = job

    def remove(self, name: str):
        if name in self._tasks:
            self._tasks[name].cancel()
            del self._tasks[name]
        self._jobs.pop(name, None)

    def start_all(self):
        for name, job in self._jobs.items():
            if job.enabled and name not in self._tasks:
                self._tasks[name] = asyncio.create_task(self._run_job(job))

    def stop_all(self):
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    async def _run_job(self, job: Job):
        """单个 Job 的运行循环。"""
        try:
            if job.interval:
                await self._run_interval(job)
            elif job.cron:
                await self._run_cron(job)
        except asyncio.CancelledError:
            pass

    async def _run_interval(self, job: Job):
        while True:
            await asyncio.sleep(job.interval)
            if not job.enabled:
                continue
            await self._emit(job)

    async def _run_cron(self, job: Job):
        """简易 cron 解析：支持 '*/N * * * *'（每 N 分钟）等基础格式。"""
        interval = _parse_simple_cron(job.cron)
        while True:
            now = time.time()
            next_run = ((now // interval) + 1) * interval
            await asyncio.sleep(max(next_run - now, 1))
            if not job.enabled:
                continue
            await self._emit(job)

    async def _emit(self, job: Job):
        await self._controller.emit(
            Interrupt(
                type=InterruptType.TIMER,
                payload={"job": job.name, "data": job.payload},
            )
        )


def _parse_simple_cron(expr: str) -> float:
    """
    极简 cron 解析，支持:
      '*/N * * * *' → 每 N 分钟
      '0 */N * * *' → 每 N 小时
    不匹配则默认 60 秒。
    """
    parts = expr.strip().split()
    if len(parts) >= 5:
        minute_field = parts[0]
        hour_field = parts[1]

        if minute_field.startswith("*/"):
            try:
                return float(minute_field[2:]) * 60
            except ValueError:
                pass

        if minute_field == "0" and hour_field.startswith("*/"):
            try:
                return float(hour_field[2:]) * 3600
            except ValueError:
                pass

    return 60.0
