"""
消息管理 — 维护多会话对话历史。

每个 session_id 独立管理历史，防止跨渠道污染。
"""
from agent.prompt import system_message

MAX_HISTORY = 50


class MessageStore:
    def __init__(self):
        self._system = system_message()
        self._sessions: dict[str, list[dict]] = {}

    def _history(self, sid: str) -> list[dict]:
        if sid not in self._sessions:
            self._sessions[sid] = []
        return self._sessions[sid]

    def add_user(self, sid: str, content: str):
        self._history(sid).append({"role": "user", "content": content})
        self._trim(sid)

    def add_assistant(self, sid: str, message: dict):
        """添加完整的 assistant message dict（含 tool_calls）。"""
        self._history(sid).append(message)
        self._trim(sid)

    def add_tool_result(self, sid: str, tool_call_id: str, content: str):
        self._history(sid).append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        self._trim(sid)

    def to_messages(self, sid: str) -> list[dict]:
        return [self._system] + self._history(sid)

    def _trim(self, sid: str):
        h = self._history(sid)
        if len(h) > MAX_HISTORY:
            self._sessions[sid] = h[-MAX_HISTORY:]
