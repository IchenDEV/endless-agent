"""
工具系统 — 唯一的工具是 Bash。

负责解析 LLM 输出中的 tool call，执行命令，返回结果。
"""
import asyncio
import json
import re
from dataclasses import dataclass


@dataclass
class ToolCall:
    command: str


@dataclass
class ToolResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int


TOOL_CALL_PATTERN = re.compile(
    r'\{\s*"tool"\s*:\s*"bash"\s*,\s*"command"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
    re.DOTALL,
)


def parse_tool_calls(text: str) -> list[ToolCall]:
    """从 LLM 输出中提取所有 bash tool call。"""
    calls = []
    for match in TOOL_CALL_PATTERN.finditer(text):
        raw = match.group(1)
        command = raw.encode().decode("unicode_escape")
        calls.append(ToolCall(command=command))
    return calls


async def execute(call: ToolCall, timeout: float = 30.0) -> ToolResult:
    """执行单个 bash 命令，返回结果。"""
    try:
        proc = await asyncio.create_subprocess_shell(
            call.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return ToolResult(
            command=call.command,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            exit_code=proc.returncode or 0,
        )
    except asyncio.TimeoutError:
        proc.kill()
        return ToolResult(
            command=call.command,
            stdout="",
            stderr=f"Command timed out after {timeout}s",
            exit_code=-1,
        )
    except Exception as e:
        return ToolResult(
            command=call.command,
            stdout="",
            stderr=str(e),
            exit_code=-1,
        )


def format_result(result: ToolResult) -> str:
    """将工具执行结果格式化为反馈给 LLM 的文本。"""
    parts = [f"$ {result.command}"]
    if result.stdout:
        parts.append(result.stdout.rstrip())
    if result.stderr:
        parts.append(f"[stderr] {result.stderr.rstrip()}")
    parts.append(f"[exit_code: {result.exit_code}]")
    return "\n".join(parts)
