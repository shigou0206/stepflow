# stepflow/worker/tools/base_tool.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class ITool(ABC):
    """
    各种执行工具的统一接口，提供 run(input_data) -> result_data
    """

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行某种操作（Shell、HTTP、REST...），
        传入 input_data (JSON dict),
        返回 result_data (JSON dict).
        """
        pass