"""
消息管理 — 维护对话历史。

保持上下文窗口在可控范围内，防止 token 爆炸。
"""
from agent.prompt import system_message

MAX_HISTORY = 50


class MessageStore:
    def __init__(self):
        self._system = system_message()
        self._history: list[dict] = []

    def add_user(self, content: str):
        self._history.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content: str):
        self._history.append({"role": "assistant", "content": content})
        self._trim()

    def add_tool_result(self, content: str):
        """工具结果以 user 角色追加（模拟 tool output 反馈给 LLM）。"""
        self._history.append({"role": "user", "content": f"[Tool Output]\n{content}"})
        self._trim()

    def to_messages(self) -> list[dict]:
        return [self._system] + self._history

    def _trim(self):
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]
