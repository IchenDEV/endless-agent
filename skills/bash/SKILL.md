---
name: bash
description: Execute shell commands to interact with the operating system. Use when asked to run commands, read/write files, install packages, check system status, or perform any terminal operation.
compatibility: Requires bash shell
metadata:
  author: agent-loop
  version: "1.0"
allowed-tools: bash
---

# Bash Skill

Execute arbitrary bash commands and return stdout/stderr.

## When to Use

- Run any system command (`ls`, `cat`, `grep`, `curl`, etc.)
- Read files: `cat /path/to/file`
- Write files: use heredoc `cat << 'EOF' > file`
- Install packages: `pip install ...`, `apt install ...`
- Check system info: `uname -a`, `df -h`, `free -m`

## Usage

Call the `run_skill_script` tool with:
- `skill`: `bash`
- `script`: `run`
- `args`: `{"command": "your-command-here"}`

## Safety Rules

1. **Dangerous commands** (`rm -rf /`, `mkfs`, `dd`) — ask user to confirm first.
2. **Long output** — pipe through `| head -50` or `| tail -20`.
3. **Multi-line file writes** — use heredoc with single-quoted delimiter: `cat << 'EOF' > file`.
4. **Background tasks** — append `&` or use `nohup`.

## Examples

### List files
```bash
ls -la /workspace
```

### Write a file
```bash
cat << 'EOF' > /tmp/hello.txt
Hello World
EOF
```

### Check disk space
```bash
df -h
```
