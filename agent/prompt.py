"""
提示词构建 — 从 Markdown 文件组装 system prompt。

读取 SOUL.md + Agent.md + Tool.md，拼接为系统消息。
可动态注入 Skills 广告信息。
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_md(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt(skills_advertise: str = "") -> str:
    soul = load_md("SOUL.md")
    agent = load_md("Agent.md")
    tool = load_md("Tool.md")
    parts = [soul, agent, tool]
    if skills_advertise:
        parts.append(skills_advertise)
    return "\n\n---\n\n".join(parts)


def system_message(skills_advertise: str = "") -> dict:
    return {"role": "system", "content": build_system_prompt(skills_advertise)}
