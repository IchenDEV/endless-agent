# Agent Loop

一个永不停止的终端 AI Agent，采用**中断驱动**事件循环 + **微软 Agent Skills 规范**。

## 核心设计

```
┌────────────────────────────────────────────────────┐
│                 Agent Event Loop                   │
│                                                    │
│  ┌──────┐   ┌──────────┐   ┌─────┐   ┌─────────┐  │
│  │ Idle │──▶│ Interrupt │──▶│ LLM │──▶│  Skill  │  │
│  │(wait)│◀──│ Dispatch  │◀──│(FC) │◀──│  Exec   │  │
│  └──────┘   └──────────┘   └─────┘   └─────────┘  │
│       ▲                                    │       │
│       │          ┌──────────┐              │       │
│       └──────────│Scheduler │──────────────┘       │
│                  └──────────┘                      │
└────────────────────────────────────────────────────┘
         ▲                         │
         │ stdin                   │ stdout
    ┌─────────┐               ┌─────────┐
    │  用户   │               │  终端   │
    └─────────┘               └─────────┘
```

### 类比 CPU 中断模型

| 概念 | CPU | Agent Loop |
|------|-----|------------|
| 主循环 | fetch-decode-execute | wait → dispatch → process |
| 中断源 | 键盘/定时器 | stdin / Scheduler |
| 中断控制器 | PIC/APIC | InterruptController |
| 中断处理 | ISR | _handle_user() |
| 指令集 | x86/ARM | Skills (function calling) |

## Agent Skills（微软规范）

遵循 [Agent Skills 开放规范](https://learn.microsoft.com/en-us/agent-framework/agents/skills)，渐进式披露：

1. **Advertise** (~100 tokens/skill) — 启动时注入 skill 名字+描述到 system prompt
2. **load_skill** — 按需加载完整 SKILL.md 指令
3. **read_skill_resource** — 按需读取参考文件
4. **run_skill_script** — 执行 skill 脚本

### Skill 目录结构

```
skills/
└── bash/
    ├── SKILL.md              # YAML frontmatter + 指令
    └── scripts/
        └── run.py            # 可执行脚本
```

### 创建新 Skill

在 `skills/` 下新建目录，包含一个 `SKILL.md`：

```yaml
---
name: my-skill
description: 做某件事。当用户问到 xxx 时使用。
metadata:
  version: "1.0"
---

# My Skill

详细使用说明...
```

可选添加 `scripts/`（可执行脚本）和 `references/`、`assets/`（资源文件）。

## 三层提示词

| 文件 | 作用 |
|------|------|
| `prompts/SOUL.md` | Agent 人格 |
| `prompts/Agent.md` | Agent 行为（中断模型 + Skill 渐进披露流程） |
| `prompts/Tool.md` | 内置 tool 说明（load_skill / read_skill_resource / run_skill_script） |

## 快速开始

```bash
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
python main.py
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | 必需 |
| `OPENAI_BASE_URL` | API 地址 | OpenAI 官方 |
| `AGENT_MODEL` | 模型名 | gpt-4o-mini |

## 定时任务

```python
from agent.scheduler import Job
scheduler.add(Job(name="check", payload="检查系统状态", interval=300))
scheduler.add(Job(name="report", payload="生成报告", cron="0 */1 * * *"))
```

## 项目结构

```
.
├── main.py                # 入口
├── agent/
│   ├── loop.py            # 核心事件循环
│   ├── interrupt.py       # 中断系统
│   ├── skill.py           # Skills Provider（微软规范）
│   ├── llm.py             # OpenAI SDK 客户端
│   ├── prompt.py          # 提示词构建
│   ├── message.py         # 对话历史管理
│   └── scheduler.py       # 定时任务调度器
├── skills/
│   └── bash/
│       ├── SKILL.md       # Bash Skill 定义
│       └── scripts/
│           └── run.py     # 命令执行脚本
├── prompts/
│   ├── SOUL.md            # 人格
│   ├── Agent.md           # 行为
│   └── Tool.md            # 工具
└── requirements.txt
```
