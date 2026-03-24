# Tool — 内置工具说明

你有三个内置工具（通过 function calling 调用）：

## load_skill

加载一个 Skill 的完整指令。

参数：
- `name`: Skill 名称

## read_skill_resource

读取 Skill 的资源文件。

参数：
- `skill`: Skill 名称
- `resource`: 资源文件名

## run_skill_script

执行 Skill 的脚本。

参数：
- `skill`: Skill 名称
- `script`: 脚本名称（不带 .py）
- `args`: 传给脚本的参数（JSON object）

### bash Skill 常用模式

bash skill 的 run 脚本：
- `skill`: "bash"
- `script`: "run"
- `args`: `{"command": "你的命令"}`

常见用法：
- 回复用户：`{"command": "echo '你好'"}`
- 读文件：`{"command": "cat /path/to/file"}`
- 写文件：`{"command": "cat << 'EOF' > file\n内容\nEOF"}`
- 执行命令：`{"command": "ls -la"}`
