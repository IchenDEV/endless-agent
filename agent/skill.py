"""
Skill 注册系统 — Agent 的能力表。

每个 Skill 就是一个 OpenAI function calling 的 tool definition + handler。
Skill 通过装饰器注册，Agent 自动发现并暴露给 LLM。
"""
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class Skill:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Awaitable[str]]


_registry: dict[str, Skill] = {}


def register(
    name: str,
    description: str,
    parameters: dict | None = None,
):
    """装饰器：注册一个 Skill。"""
    if parameters is None:
        parameters = {"type": "object", "properties": {}, "required": []}

    def decorator(fn: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        _registry[name] = Skill(
            name=name,
            description=description,
            parameters=parameters,
            handler=fn,
        )
        return fn

    return decorator


def get_all() -> list[Skill]:
    return list(_registry.values())


def get(name: str) -> Skill | None:
    return _registry.get(name)


def to_openai_tools() -> list[dict]:
    """转换为 OpenAI function calling 的 tools 格式。"""
    return [
        {
            "type": "function",
            "function": {
                "name": s.name,
                "description": s.description,
                "parameters": s.parameters,
            },
        }
        for s in _registry.values()
    ]


async def execute(name: str, arguments: str) -> str:
    """执行指定 Skill，返回结果字符串。"""
    skill = _registry.get(name)
    if not skill:
        return json.dumps({"error": f"Unknown skill: {name}"})

    try:
        args = json.loads(arguments) if arguments else {}
        return await skill.handler(**args)
    except Exception as e:
        return json.dumps({"error": str(e)})
