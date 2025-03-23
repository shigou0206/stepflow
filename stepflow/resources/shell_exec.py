# stepflow/resources/shell_exec.py
import subprocess

def run(params: dict, context: dict) -> dict:
    """
    最简单的示例: 直接执行shell命令.
    params = { "command": "echo Hello" }
    """
    cmd = params.get("command")
    if not cmd:
        raise Exception("ShellError: 'command' parameter is required.")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "stdout": result.stdout.strip(),
        "exit_code": result.returncode
    }