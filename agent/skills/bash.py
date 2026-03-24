"""
Bash Skill — 执行 shell 命令。
"""
import asyncio

from agent.skill import register


@register(
    name="bash",
    description="Execute a bash command and return stdout/stderr. Use this for all system operations: running commands, reading/writing files, installing packages, etc.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute",
            },
        },
        "required": ["command"],
    },
)
async def bash_skill(command: str) -> str:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        parts = []
        if stdout:
            parts.append(stdout.decode(errors="replace").rstrip())
        if stderr:
            parts.append(f"[stderr] {stderr.decode(errors='replace').rstrip()}")
        parts.append(f"[exit_code: {proc.returncode or 0}]")
        return "\n".join(parts)
    except asyncio.TimeoutError:
        proc.kill()
        return "[error] Command timed out after 30s"
    except Exception as e:
        return f"[error] {e}"
