# stepflow/worker/tools/tool_registry.py

from .base_tool import ITool
from .shell_tool import ShellTool
from .http_tool import HttpTool

# 你也可以 import 其他 tool，比如 EmailTool、DBTool 等

tool_registry = {
    "shell": ShellTool(),   # activity_type="shell" 时调用此对象
    "http": HttpTool(),     # activity_type="http"  时调用此对象
    # "email": EmailTool(),
    # ...
}