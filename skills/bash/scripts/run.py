"""
bash skill script — 执行 shell 命令。

被 run_skill_script tool 调用：
  args: {"command": "..."}
"""
import subprocess
import sys
import json


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    command = args.get("command", "")
    if not command:
        print(json.dumps({"error": "No command provided"}))
        sys.exit(1)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        parts = []
        if result.stdout:
            parts.append(result.stdout.rstrip())
        if result.stderr:
            parts.append(f"[stderr] {result.stderr.rstrip()}")
        parts.append(f"[exit_code: {result.returncode}]")
        print("\n".join(parts))
    except subprocess.TimeoutExpired:
        print("[error] Command timed out after 30s")
        sys.exit(1)
    except Exception as e:
        print(f"[error] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
