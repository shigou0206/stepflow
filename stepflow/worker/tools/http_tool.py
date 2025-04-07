# stepflow/worker/tools/http_tool.py

import aiohttp
import json
import logging
from typing import Dict, Any, Optional, Union, List
from .base_tool import ITool

logger = logging.getLogger(__name__)

class HttpTool(ITool):
    """增强版 HTTP 工具，支持完整的 REST API 功能"""
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 HTTP 请求并返回结果
        
        支持的输入参数:
        - url: 请求地址 (必需)
        - method: 请求方法 (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)，默认为 GET
        - headers: 请求头，字典格式
        - params: URL 查询参数，字典格式
        - data: 表单数据，字典格式或字符串
        - json: JSON 数据，字典格式
        - timeout: 超时时间（秒），默认 30 秒
        - verify_ssl: 是否验证 SSL 证书，默认 True
        - allow_redirects: 是否允许重定向，默认 True
        - proxy: 代理服务器 URL
        - auth: 基本认证信息，格式为 [username, password]
        - cookies: Cookie 信息，字典格式
        - parse_json: 是否尝试解析 JSON 响应，默认 True
        
        返回结果:
        - status: HTTP 状态码
        - headers: 响应头
        - body: 响应体（如果 parse_json=True 且响应是有效 JSON，则为解析后的对象）
        - json: 如果响应是有效 JSON，则为解析后的对象
        - text: 响应文本
        - cookies: 响应 Cookie
        - elapsed: 请求耗时（毫秒）
        - url: 最终 URL（考虑重定向后）
        - ok: 请求是否成功（状态码 < 400）
        - error: 如果请求失败，包含错误信息
        """
        # 提取必需参数
        url = input_data.get("url")
        if not url:
            return {"error": "No 'url' provided", "ok": False}
        
        # 提取可选参数
        method = input_data.get("method", "GET").upper()
        headers = input_data.get("headers", {})
        params = input_data.get("params", {})
        data = input_data.get("data", None)
        json_data = input_data.get("json", None)
        timeout = input_data.get("timeout", 30)
        verify_ssl = input_data.get("verify_ssl", True)
        allow_redirects = input_data.get("allow_redirects", True)
        proxy = input_data.get("proxy", None)
        auth = input_data.get("auth", None)
        cookies = input_data.get("cookies", {})
        parse_json = input_data.get("parse_json", True)
        
        # 验证方法
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if method not in valid_methods:
            return {
                "error": f"Invalid method: {method}. Must be one of {valid_methods}",
                "ok": False
            }
        
        # 准备 aiohttp 请求参数
        request_kwargs = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "ssl": verify_ssl,
            "allow_redirects": allow_redirects,
            "timeout": aiohttp.ClientTimeout(total=timeout),
            "cookies": cookies
        }
        
        # 添加认证信息
        if auth and isinstance(auth, list) and len(auth) == 2:
            request_kwargs["auth"] = aiohttp.BasicAuth(auth[0], auth[1])
        
        # 添加代理
        if proxy:
            request_kwargs["proxy"] = proxy
        
        # 添加请求体
        if json_data is not None:
            request_kwargs["json"] = json_data
        elif data is not None:
            request_kwargs["data"] = data
        
        # 在请求开始前添加
        logger.info(f"开始 HTTP 请求: {method} {url}")
        
        # 执行请求
        start_time = None
        try:
            async with aiohttp.ClientSession() as session:
                import time
                start_time = time.time()
                async with session.request(**request_kwargs) as response:
                    elapsed = int((time.time() - start_time) * 1000)  # 毫秒
                    
                    # 在请求成功后添加
                    logger.info(f"HTTP 请求成功: {method} {url}, 状态码: {response.status}")
                    
                    # 准备响应数据
                    result = {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "cookies": dict(response.cookies),
                        "elapsed": elapsed,
                        "url": str(response.url),
                        "ok": response.status < 400
                    }
                    
                    # 获取响应体
                    body = await response.text()
                    result["text"] = body
                    
                    # 尝试解析 JSON
                    if parse_json and body:
                        try:
                            json_body = json.loads(body)
                            result["json"] = json_body
                            result["body"] = json_body
                        except json.JSONDecodeError:
                            result["body"] = body
                    else:
                        result["body"] = body
                    
                    return result
                    
        except aiohttp.ClientError as e:
            elapsed = int((time.time() - start_time) * 1000) if start_time else None
            # 在请求失败时添加
            logger.error(f"HTTP 请求失败: {method} {url}, 错误: {str(e)}")
            return {
                "error": f"Request failed: {str(e)}",
                "elapsed": elapsed,
                "ok": False
            }
        except Exception as e:
            elapsed = int((time.time() - start_time) * 1000) if start_time else None
            logger.error(f"Unexpected error in HTTP tool: {str(e)}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "elapsed": elapsed,
                "ok": False
            }