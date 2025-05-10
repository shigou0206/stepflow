from .base_tool import ITool
from .shell_tool import ShellTool
from .http_tool import HttpTool

# 你也可以 import 其他 tool，比如 EmailTool、DBTool 等

# 检查工具注册表

# 工具注册表
tool_registry = {
    "HttpTool": HttpTool(),
    "ShellTool": ShellTool(),
    # 其他工具...
}