# Agent Loop

一个永不停止的终端 AI Agent，采用**中断驱动**的事件循环架构。

## 核心设计

```
┌─────────────────────────────────────────────┐
│              Agent Event Loop               │
│                                             │
│   ┌─────────┐    ┌──────────┐    ┌───────┐  │
│   │ Idle    │───▶│ Interrupt│───▶│Process│  │
│   │ (wait)  │◀───│ Dispatch │◀───│ (LLM) │  │
│   └─────────┘    └──────────┘    └───┬───┘  │
│                                      │      │
│                                 ┌────▼────┐ │
│                                 │  Bash   │ │
│                                 │  Tool   │ │
│                                 └─────────┘ │
└─────────────────────────────────────────────┘
         ▲                    │
         │ stdin (中断源)      │ stdout (工具输出)
         │                    ▼
    ┌─────────┐          ┌─────────┐
    │  用户   │          │  终端   │
    └─────────┘          └─────────┘
```

### 类比 CPU 中断模型

| 概念 | CPU | Agent Loop |
|------|-----|------------|
| 主循环 | fetch-decode-execute | wait-dispatch-process |
| 中断源 | 键盘/网卡/定时器 | stdin/signal/timer |
| 中断控制器 | PIC/APIC | InterruptController |
| 中断处理 | ISR | handle_user_input() |
| 工具 | I/O 指令 | bash command |

## 三层提示词

| 文件 | 作用 |
|------|------|
| `prompts/SOUL.md` | Agent 的人格：务实、谦逊、主动 |
| `prompts/Agent.md` | Agent 的行为：事件循环模型、处理策略 |
| `prompts/Tool.md` | 工具使用：bash 命令格式、安全规则 |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key
export OPENAI_API_KEY="your-key"

# 可选：自定义模型和 API 地址
export AGENT_MODEL="gpt-4o-mini"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# 启动
python main.py
```

## 项目结构

```
.
├── main.py              # 入口
├── agent/
│   ├── interrupt.py     # 中断系统（中断控制器 + stdin 监听）
│   ├── loop.py          # 核心事件循环（永不停止）
│   ├── tool.py          # Bash 工具（解析 + 执行）
│   ├── llm.py           # LLM 客户端（OpenAI 兼容）
│   ├── prompt.py        # 提示词构建（从 md 文件组装）
│   └── message.py       # 对话历史管理
├── prompts/
│   ├── SOUL.md          # 人格定义
│   ├── Agent.md         # 行为规范
│   └── Tool.md          # 工具说明
└── requirements.txt
```

## 工作流程

1. 启动后进入 idle 状态，等待中断
2. 用户在终端输入文本，触发 `USER_INPUT` 中断
3. 中断控制器将输入放入队列，唤醒主循环
4. 主循环调用 LLM，LLM 返回包含 `{"tool": "bash", "command": "..."}` 的响应
5. Agent 解析并执行 bash 命令，将结果反馈给 LLM
6. 重复 4-5 直到 LLM 不再发出 tool call
7. 回到 idle，等待下一个中断
