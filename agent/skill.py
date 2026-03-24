"""
Skill Provider — 遵循微软 Agent Skills 规范。

从 skills/ 目录递归发现 SKILL.md，实现渐进式披露：
  1. Advertise — 名字+描述注入 system prompt (~100 tokens/skill)
  2. load_skill — 按需加载完整 SKILL.md 指令
  3. read_skill_resource — 按需读取附带资源文件
  4. run_skill_script — 执行 skill 目录下的脚本

这三个函数作为 OpenAI function calling tools 暴露给 LLM。
"""
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SkillScript:
    name: str
    path: Path
    description: str = ""


@dataclass
class SkillResource:
    name: str
    path: Path


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    frontmatter: dict = field(default_factory=dict)
    body: str = ""
    scripts: list[SkillScript] = field(default_factory=list)
    resources: list[SkillResource] = field(default_factory=list)


class SkillsProvider:
    """从文件系统发现和管理 Skills。"""

    def __init__(self, skill_paths: list[Path] | Path):
        if isinstance(skill_paths, Path):
            skill_paths = [skill_paths]
        self._paths = skill_paths
        self._skills: dict[str, Skill] = {}
        self._discover()

    def _discover(self):
        """递归搜索 SKILL.md（最多两层深）。"""
        for base in self._paths:
            if not base.exists():
                continue
            for skill_md in base.rglob("SKILL.md"):
                depth = len(skill_md.relative_to(base).parts) - 1
                if depth > 2:
                    continue
                skill = _parse_skill(skill_md)
                if skill and skill.name not in self._skills:
                    self._skills[skill.name] = skill

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def advertise_text(self) -> str:
        """生成注入 system prompt 的技能列表（短描述）。"""
        if not self._skills:
            return ""
        lines = ["## Available Skills\n"]
        for s in self._skills.values():
            lines.append(f"- **{s.name}**: {s.description}")
        lines.append("")
        lines.append("Use `load_skill` to load a skill's full instructions.")
        lines.append("Use `read_skill_resource` to read skill resources.")
        lines.append("Use `run_skill_script` to execute skill scripts.")
        return "\n".join(lines)


# ── OpenAI Function Calling Tools ──

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": "Load the full instructions of a skill by name. Returns the SKILL.md body content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The skill name to load",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill_resource",
            "description": "Read a resource file from a skill. Returns the file content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "The skill name",
                    },
                    "resource": {
                        "type": "string",
                        "description": "The resource file name",
                    },
                },
                "required": ["skill", "resource"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_skill_script",
            "description": "Run a script from a skill. For the bash skill, pass {\"command\": \"your-command\"} as args.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "The skill name",
                    },
                    "script": {
                        "type": "string",
                        "description": "The script name (without .py extension)",
                    },
                    "args": {
                        "type": "object",
                        "description": "Arguments to pass to the script as JSON",
                    },
                },
                "required": ["skill", "script"],
            },
        },
    },
]


async def handle_tool_call(provider: SkillsProvider, name: str, arguments: str) -> str:
    """统一处理三个 skill tool call。"""
    args = json.loads(arguments) if arguments else {}

    if name == "load_skill":
        return _load_skill(provider, args.get("name", ""))

    if name == "read_skill_resource":
        return _read_resource(provider, args.get("skill", ""), args.get("resource", ""))

    if name == "run_skill_script":
        return await _run_script(
            provider, args.get("skill", ""), args.get("script", ""), args.get("args", {})
        )

    return json.dumps({"error": f"Unknown tool: {name}"})


def _load_skill(provider: SkillsProvider, name: str) -> str:
    skill = provider.get_skill(name)
    if not skill:
        available = [s.name for s in provider.list_skills()]
        return json.dumps({"error": f"Skill '{name}' not found. Available: {available}"})

    parts = [skill.body]
    if skill.scripts:
        parts.append("\n### Scripts")
        for s in skill.scripts:
            parts.append(f"- `{s.name}`: {s.description or s.path.name}")
    if skill.resources:
        parts.append("\n### Resources")
        for r in skill.resources:
            parts.append(f"- `{r.name}`")
    return "\n".join(parts)


def _read_resource(provider: SkillsProvider, skill_name: str, resource_name: str) -> str:
    skill = provider.get_skill(skill_name)
    if not skill:
        return json.dumps({"error": f"Skill '{skill_name}' not found"})

    for r in skill.resources:
        if r.name == resource_name:
            try:
                return r.path.read_text(encoding="utf-8")
            except Exception as e:
                return json.dumps({"error": str(e)})

    available = [r.name for r in skill.resources]
    return json.dumps({"error": f"Resource '{resource_name}' not found. Available: {available}"})


async def _run_script(
    provider: SkillsProvider, skill_name: str, script_name: str, args: dict
) -> str:
    skill = provider.get_skill(skill_name)
    if not skill:
        return json.dumps({"error": f"Skill '{skill_name}' not found"})

    script = None
    for s in skill.scripts:
        if s.name == script_name:
            script = s
            break

    if not script:
        available = [s.name for s in skill.scripts]
        return json.dumps({"error": f"Script '{script_name}' not found. Available: {available}"})

    try:
        result = subprocess.run(
            [sys.executable, str(script.path), json.dumps(args)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr] {result.stderr.rstrip()}"
        if result.returncode != 0:
            output += f"\n[exit_code: {result.returncode}]"
        return output.strip() if output.strip() else "[no output]"
    except subprocess.TimeoutExpired:
        return "[error] Script timed out after 30s"
    except Exception as e:
        return f"[error] {e}"


# ── SKILL.md 解析 ──

def _parse_skill(skill_md: Path) -> Skill | None:
    """解析一个 SKILL.md 文件，返回 Skill 对象。"""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except Exception:
        return None

    frontmatter, body = _split_frontmatter(text)
    if not frontmatter.get("name") or not frontmatter.get("description"):
        return None

    skill_dir = skill_md.parent
    scripts = _discover_scripts(skill_dir)
    resources = _discover_resources(skill_dir)

    return Skill(
        name=frontmatter["name"],
        description=frontmatter["description"],
        path=skill_dir,
        frontmatter=frontmatter,
        body=body.strip(),
        scripts=scripts,
        resources=resources,
    )


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """分离 YAML frontmatter 和 markdown body。"""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}

    return fm, parts[2]


def _discover_scripts(skill_dir: Path) -> list[SkillScript]:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return []
    result = []
    for py in sorted(scripts_dir.glob("*.py")):
        result.append(SkillScript(
            name=py.stem,
            path=py,
            description=f"Run {py.name}",
        ))
    return result


def _discover_resources(skill_dir: Path) -> list[SkillResource]:
    resources = []
    for subdir in ("references", "assets"):
        d = skill_dir / subdir
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file():
                resources.append(SkillResource(name=f.name, path=f))
    return resources
