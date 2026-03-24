"""
消息管理 — 维护对话历史。

保持上下文窗口可控，防止 token 爆炸。
使用 OpenAI message 格式（含 tool role）。
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

    def add_assistant(self, message: dict):
        """添加完整的 assistant message（可含 tool_calls）。"""
        self._history.append(message)
        self._trim()

    def add_tool_result(self, tool_call_id: str, content: str):
        self._history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        self._trim()

    def to_messages(self) -> list[dict]:
        return [self._system] + self._history

    def _trim(self):
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]
