"""
提示词构建 — 从 Markdown 文件组装 system prompt。

读取 SOUL.md + Agent.md + Tool.md，拼接为系统消息。
"""
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_md(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt() -> str:
    soul = load_md("SOUL.md")
    agent = load_md("Agent.md")
    tool = load_md("Tool.md")
    return f"{soul}\n\n---\n\n{agent}\n\n---\n\n{tool}"


def system_message() -> dict:
    return {"role": "system", "content": build_system_prompt()}
