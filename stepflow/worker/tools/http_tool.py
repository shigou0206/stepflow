# stepflow/worker/tools/http_tool.py

import aiohttp
from typing import Dict, Any
from .base_tool import ITool

class HttpTool(ITool):
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        input_data 里可包含:
          "url": 请求地址,
          "method": "GET"/"POST" (默认"GET")
          "headers": dict,
          "payload": JSON

        这里简单发 HTTP 请求并返回 status/body
        """
        url = input_data.get("url")
        if not url:
            return {"error": "No 'url' provided"}

        method = input_data.get("method", "GET").upper()
        headers = input_data.get("headers", {})
        payload = input_data.get("payload", None)

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=headers, json=payload
            ) as resp:
                body = await resp.text()
                return {
                    "status": resp.status,
                    "body": body
                }