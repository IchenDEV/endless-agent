"""
Web 渠道 — FastAPI + Vercel AI SDK UI Message Stream Protocol。

兼容 Vercel useChat() 前端组件。
"""
import asyncio
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agent.channels.base import Channel
from agent.interrupt import Interrupt, InterruptController, InterruptType


class WebChannel(Channel):
    """HTTP API 渠道，每个请求是一个中断。响应通过 SSE 流回前端。"""

    def __init__(self, controller: InterruptController, host: str = "0.0.0.0", port: int = 3000):
        self._controller = controller
        self._host = host
        self._port = port
        self._app = FastAPI()
        self._pending: dict[str, asyncio.Queue[dict | None]] = {}
        self._setup_routes()
        self._server = None

    @property
    def name(self) -> str:
        return "web"

    def _setup_routes(self):
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self._app.post("/api/chat")
        async def chat(request: Request):
            body = await request.json()
            messages = body.get("messages", [])
            if not messages:
                return {"error": "No messages"}

            last_msg = messages[-1]
            text = _extract_text(last_msg)
            session_id = body.get("id", str(uuid.uuid4()))

            event_queue: asyncio.Queue[dict | None] = asyncio.Queue()
            self._pending[session_id] = event_queue

            await self._controller.emit(
                Interrupt(
                    type=InterruptType.USER_INPUT,
                    payload=text,
                    channel="web",
                    session_id=session_id,
                )
            )

            return StreamingResponse(
                _sse_generator(event_queue),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "x-vercel-ai-ui-message-stream": "v1",
                },
            )

        @self._app.get("/health")
        async def health():
            return {"status": "ok"}

    async def start(self):
        import uvicorn
        config = uvicorn.Config(
            self._app,
            host=self._host,
            port=self._port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)
        asyncio.create_task(self._server.serve())

    async def stop(self):
        if self._server:
            self._server.should_exit = True
        for q in self._pending.values():
            await q.put(None)
        self._pending.clear()

    async def send_text(self, session_id: str, text: str):
        q = self._pending.get(session_id)
        if not q:
            return
        part_id = str(uuid.uuid4())
        await q.put({"type": "text-start", "id": part_id})
        await q.put({"type": "text-delta", "id": part_id, "delta": text})
        await q.put({"type": "text-end", "id": part_id})

    async def send_tool_output(self, session_id: str, tool_name: str, command: str, output: str):
        q = self._pending.get(session_id)
        if not q:
            return
        part_id = str(uuid.uuid4())
        display = f"```\n$ {command}\n{output}\n```"
        await q.put({"type": "text-start", "id": part_id})
        await q.put({"type": "text-delta", "id": part_id, "delta": display})
        await q.put({"type": "text-end", "id": part_id})

    async def finish(self, session_id: str):
        """发送完成信号并清理。"""
        q = self._pending.get(session_id)
        if not q:
            return
        await q.put({"type": "finish"})
        await q.put(None)
        self._pending.pop(session_id, None)


def _extract_text(msg: dict) -> str:
    """从 Vercel useChat 消息格式中提取纯文本。"""
    if isinstance(msg.get("content"), str):
        return msg["content"]
    parts = msg.get("parts", [])
    texts = []
    for p in parts:
        if isinstance(p, dict) and p.get("type") == "text":
            texts.append(p.get("text", ""))
    return "\n".join(texts) if texts else str(msg)


import json

async def _sse_generator(queue: asyncio.Queue[dict | None]) -> AsyncGenerator[str, None]:
    """从事件队列生成 SSE 流。"""
    msg_id = str(uuid.uuid4())
    yield f"data: {json.dumps({'type': 'start', 'messageId': msg_id})}\n\n"
    yield f"data: {json.dumps({'type': 'start-step'})}\n\n"

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"

    yield f"data: {json.dumps({'type': 'finish-step'})}\n\n"
    yield f"data: {json.dumps({'type': 'finish'})}\n\n"
    yield "data: [DONE]\n\n"
