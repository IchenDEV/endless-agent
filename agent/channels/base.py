"""
Channel 基类 — 定义渠道接口。

每个渠道（CLI、Web、Slack 等）实现这个接口，
负责接收用户输入（触发中断）和向用户发送 Agent 输出。
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class Channel(ABC):
    """所有通信渠道的基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """渠道标识符。"""
        ...

    @abstractmethod
    async def start(self):
        """启动渠道（如开始监听 stdin、启动 web server 等）。"""
        ...

    @abstractmethod
    async def stop(self):
        """停止渠道。"""
        ...

    @abstractmethod
    async def send_text(self, session_id: str, text: str):
        """向指定会话发送文本。"""
        ...

    @abstractmethod
    async def send_tool_output(self, session_id: str, tool_name: str, command: str, output: str):
        """向指定会话发送工具执行结果。"""
        ...
