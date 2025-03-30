# stepflow/worker/tools/shell_tool.py

import subprocess
from typing import Dict, Any
from .base_tool import ITool

class ShellTool(ITool):
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        通过 subprocess.run 执行 Shell 命令。
        input_data 里需有 cmd，如 {"cmd":"ls -l"}。
        """
        cmd = input_data.get("cmd", "echo 'No cmd provided'")
        # 同步方式: subprocess.run，也可以改成 asyncio.create_subprocess_exec
        result = subprocess.run(cmd, shell=True, capture_output=True)

        return {
            "returncode": result.returncode,
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
        }