"""
核心事件循环 — 中断驱动的 Agent Loop。

永不停止。等待中断 → 识别渠道 → 调用 LLM (function calling) → 执行 Skill → 反馈 → 等待。
"""
import asyncio
import json

from agent.interrupt import Interrupt, InterruptController, InterruptType
from agent.message import MessageStore
from agent.channels.base import Channel
from agent.scheduler import Scheduler
from agent import llm, skill
import agent.skills  # noqa: F401 — 触发 skill 注册


MAX_TOOL_ROUNDS = 10


class AgentLoop:
    def __init__(self):
        self.controller = InterruptController()
        self.store = MessageStore()
        self.scheduler = Scheduler(self.controller)
        self._channels: dict[str, Channel] = {}

    def add_channel(self, channel: Channel):
        self._channels[channel.name] = channel

    def get_channel(self, name: str) -> Channel | None:
        return self._channels.get(name)

    async def start(self):
        for ch in self._channels.values():
            await ch.start()
        self.scheduler.start_all()

        try:
            await self._loop()
        finally:
            await self.stop()

    async def stop(self):
        self.scheduler.stop_all()
        for ch in self._channels.values():
            await ch.stop()

    async def _loop(self):
        while True:
            interrupt = await self.controller.wait()

            if interrupt.type == InterruptType.USER_INPUT:
                await self._handle_user(interrupt)

            elif interrupt.type == InterruptType.TIMER:
                await self._handle_timer(interrupt)

            elif interrupt.type == InterruptType.SIGNAL:
                if interrupt.payload == "EOF":
                    break

    async def _handle_user(self, interrupt: Interrupt):
        ch = self.get_channel(interrupt.channel)
        sid = interrupt.session_id
        try:
            await self._run_agent(sid, interrupt.payload, ch)
        except Exception as e:
            if ch:
                await ch.send_text(sid, f"[错误] {e}")

        if ch and hasattr(ch, "finish"):
            await ch.finish(sid)

    async def _handle_timer(self, interrupt: Interrupt):
        """定时任务：payload.data 作为 prompt 发给 LLM。"""
        data = interrupt.payload
        job_name = data.get("job", "unknown")
        prompt = data.get("data", f"Timer triggered: {job_name}")
        if isinstance(prompt, str):
            sid = f"timer_{job_name}"
            await self._run_agent(sid, prompt, None)

    async def _run_agent(self, sid: str, user_text: str, ch: Channel | None):
        """核心 Agent 调用循环：LLM → tool_calls → execute → feedback → repeat。"""
        self.store.add_user(sid, user_text)
        tools = skill.to_openai_tools()

        for _ in range(MAX_TOOL_ROUNDS):
            message = await llm.chat(self.store.to_messages(sid), tools=tools)

            assistant_dict = _message_to_dict(message)
            self.store.add_assistant(sid, assistant_dict)

            if not message.tool_calls:
                if message.content and ch:
                    await ch.send_text(sid, message.content)
                break

            for tc in message.tool_calls:
                result = await skill.execute(tc.function.name, tc.function.arguments)

                self.store.add_tool_result(sid, tc.id, result)

                if ch:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    cmd = args.get("command", tc.function.name)
                    await ch.send_tool_output(sid, tc.function.name, cmd, result)


def _message_to_dict(msg) -> dict:
    """ChatCompletionMessage → dict，保留 tool_calls 信息。"""
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
