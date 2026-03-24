"""
LLM 客户端 — 使用 OpenAI 官方 SDK。

支持 function calling (tool use) 和流式输出。
"""
import os
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage


DEFAULT_MODEL = "gpt-4o-mini"


def _create_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", None),
    )


def get_model() -> str:
    return os.environ.get("AGENT_MODEL", DEFAULT_MODEL)


async def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
) -> ChatCompletionMessage:
    """非流式调用，返回 ChatCompletionMessage（含 tool_calls）。"""
    client = _create_client()
    kwargs = {
        "model": get_model(),
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message


async def chat_stream(
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
):
    """流式调用，yield (delta_content, tool_calls_delta, finish_reason)。"""
    client = _create_client()
    kwargs = {
        "model": get_model(),
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if tools:
        kwargs["tools"] = tools

    stream = await client.chat.completions.create(**kwargs)
    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        finish = chunk.choices[0].finish_reason if chunk.choices else None
        yield delta, finish
