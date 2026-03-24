# Agent Loop

一个永不停止的终端 AI Agent，采用**中断驱动**的事件循环架构。

## 核心设计

```
┌───────────────────────────────────────────────────────┐
│                   Agent Event Loop                    │
│                                                       │
│   ┌─────────┐    ┌──────────┐    ┌──────┐   ┌──────┐ │
│   │  Idle   │───▶│Interrupt │───▶│ LLM  │──▶│Skill │ │
│   │ (wait)  │◀───│ Dispatch │◀───│(func │◀──│exec  │ │
│   └─────────┘    └──────────┘    │call) │   └──────┘ │
│                                  └──────┘             │
└───────────┬─────────────────────────────┬─────────────┘
            │                             │
    ┌───────┴───────┐             ┌───────┴───────┐
    │   Channels    │             │   Scheduler   │
    │ ┌───┐ ┌─────┐│             │  (Cron/Timer) │
    │ │CLI│ │ Web ││             └───────────────┘
    │ └───┘ └─────┘│
    └───────────────┘
```

### 类比 CPU 中断模型

| 概念 | CPU | Agent Loop |
|------|-----|------------|
| 主循环 | fetch-decode-execute | wait → dispatch → process |
| 中断源 | 键盘/网卡/定时器 | CLI / Web / Scheduler |
| 中断控制器 | PIC/APIC | InterruptController |
| 中断处理 | ISR | AgentLoop._handle_user() |
| 指令集 | x86/ARM | Skills (function calling) |

## 三层提示词

| 文件 | 作用 |
|------|------|
| `prompts/SOUL.md` | Agent 的人格：务实、谦逊、主动 |
| `prompts/Agent.md` | Agent 的行为：事件循环模型、Skill 调用策略 |
| `prompts/Tool.md` | Skill 使用指南：bash 等工具说明 |

## 快速开始

```bash
pip install -r requirements.txt

export OPENAI_API_KEY="your-key"

# CLI 模式
python main.py

# Web 模式（兼容 Vercel AI SDK useChat）
python main.py --web

# 同时启动
python main.py --cli --web --port 3000
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | 必需 |
| `OPENAI_BASE_URL` | API 地址 | OpenAI 官方 |
| `AGENT_MODEL` | 模型名 | gpt-4o-mini |
| `WEB_PORT` | Web 端口 | 3000 |

## Web API（Vercel AI SDK 兼容）

### POST /api/chat

兼容 Vercel AI SDK `useChat()` 的 UI Message Stream Protocol。

**请求体**：
```json
{
  "messages": [{"role": "user", "content": "hello"}],
  "id": "session-id"
}
```

**响应**：SSE 流，header `x-vercel-ai-ui-message-stream: v1`

**前端接入**：
```tsx
import { useChat } from '@ai-sdk/react';

export default function Chat() {
  const { messages, sendMessage } = useChat({
    api: 'http://localhost:3000/api/chat',
  });
  // ...
}
```

## Skill 系统

通过装饰器注册 Skill，自动转化为 OpenAI function calling tools。

```python
from agent.skill import register

@register(
    name="my_skill",
    description="做某件事",
    parameters={
        "type": "object",
        "properties": {"arg": {"type": "string"}},
        "required": ["arg"],
    },
)
async def my_skill(arg: str) -> str:
    return f"结果: {arg}"
```

### 内置 Skill

| Skill | 说明 |
|-------|------|
| `bash` | 执行 shell 命令 |

## 定时任务

```python
from agent.scheduler import Job

agent = AgentLoop()
agent.scheduler.add(Job(
    name="health_check",
    payload="检查系统状态并报告",
    interval=300,  # 每 5 分钟
))
# 或 cron 风格
agent.scheduler.add(Job(
    name="daily_report",
    payload="生成每日报告",
    cron="0 */1 * * *",  # 每小时
))
```

## 项目结构

```
.
├── main.py                  # 入口（CLI / Web 模式）
├── agent/
│   ├── loop.py              # 核心事件循环
│   ├── interrupt.py         # 中断系统
│   ├── skill.py             # Skill 注册表
│   ├── llm.py               # OpenAI SDK 客户端
│   ├── prompt.py            # 提示词构建
│   ├── message.py           # 多会话消息管理
│   ├── scheduler.py         # 定时任务调度器
│   ├── skills/
│   │   └── bash.py          # Bash Skill
│   └── channels/
│       ├── base.py          # Channel 基类
│       ├── cli.py           # CLI 渠道（stdin/stdout）
│       └── web.py           # Web 渠道（Vercel AI SDK）
├── prompts/
│   ├── SOUL.md              # 人格定义
│   ├── Agent.md             # 行为规范
│   └── Tool.md              # Skill 使用指南
└── requirements.txt
```
