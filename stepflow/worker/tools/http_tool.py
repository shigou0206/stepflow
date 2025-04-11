# stepflow/worker/tools/http_tool.py

import aiohttp
import json
import logging
import time
import traceback
from typing import Dict, Any, Optional, Union, List
from .base_tool import ITool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # 设置日志级别为 INFO

class HttpTool(ITool):
    """增强版 HTTP 工具，支持完整的 REST API 功能"""
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行 HTTP 请求"""
        # 记录开始执行的日志
        logger.info(f"开始执行 HTTP 请求: {parameters.get('method', 'GET')} {parameters.get('url')}")
        
        # 提取必需参数
        url = parameters.get("url")
        if not url:
            logger.error("HTTP 请求缺少必需参数: url")
            return {"error": "No 'url' provided", "ok": False}
        
        # 提取可选参数
        method = parameters.get("method", "GET").upper()
        headers = parameters.get("headers", {})
        params = parameters.get("params", {})
        data = parameters.get("data", None)
        json_data = parameters.get("json", None)
        timeout = parameters.get("timeout", 30)
        verify_ssl = parameters.get("verify_ssl", True)
        allow_redirects = parameters.get("allow_redirects", True)
        proxy = parameters.get("proxy", None)
        auth = parameters.get("auth", None)
        cookies = parameters.get("cookies", {})
        parse_json = parameters.get("parse_json", True)
        
        # 记录请求详情
        logger.info(f"HTTP 请求详情: 方法={method}, URL={url}")
        logger.info(f"HTTP 请求头: {headers}")
        if params:
            logger.info(f"查询参数: {params}")
        if data:
            logger.info(f"表单数据: {data}")
        if json_data:
            logger.info(f"JSON 数据: {json_data}")
        
        # 验证方法
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if method not in valid_methods:
            logger.error(f"无效的 HTTP 方法: {method}")
            return {"error": f"Invalid method: {method}", "ok": False}
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行请求
        try:
            logger.info(f"开始发送 HTTP 请求...")
            
            # 设置代理
            if proxy:
                logger.info(f"使用代理: {proxy}")
            
            # 设置超时
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            # 创建会话并发送请求
            async with aiohttp.ClientSession(cookies=cookies, timeout=timeout_obj) as session:
                # 准备请求参数
                request_kwargs = {
                    "url": url,
                    "params": params,
                    "ssl": verify_ssl,
                    "allow_redirects": allow_redirects,
                    "headers": headers
                }
                
                # 添加认证信息
                if auth:
                    request_kwargs["auth"] = aiohttp.BasicAuth(auth[0], auth[1])
                
                # 添加代理
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                # 添加请求体
                if method in ["POST", "PUT", "PATCH"]:
                    if json_data is not None:
                        request_kwargs["json"] = json_data
                    elif data is not None:
                        request_kwargs["data"] = data
                
                # 发送请求
                async with getattr(session, method.lower())(**request_kwargs) as response:
                    # 计算请求耗时
                    elapsed = int((time.time() - start_time) * 1000)
                    
                    # 获取响应内容
                    text = await response.text()
                    
                    # 尝试解析 JSON
                    body = None
                    if parse_json and text:
                        try:
                            body = json.loads(text)
                            logger.info(f"成功解析 JSON 响应")
                        except json.JSONDecodeError:
                            logger.info(f"响应不是有效的 JSON 格式")
                            body = text
                    else:
                        body = text
                    
                    # 构建结果
                    result = {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "text": text,
                        "cookies": dict(response.cookies),
                        "elapsed": elapsed,
                        "url": str(response.url),
                        "ok": response.status < 400
                    }
                    
                    # 添加解析后的 JSON 或原始响应体
                    if parse_json and isinstance(body, dict):
                        result["json"] = body
                    else:
                        result["body"] = body
                    
                    logger.info(f"HTTP 请求完成: 状态码={response.status}, 耗时={elapsed}ms")
                    return result
                    
        except aiohttp.ClientError as e:
            elapsed = int((time.time() - start_time) * 1000) if start_time else None
            error_msg = f"Request failed: {str(e)}"
            logger.error(f"HTTP 请求失败: {method} {url}, 错误: {str(e)}")
            return {
                "error": error_msg,
                "elapsed": elapsed,
                "ok": False
            }
        except Exception as e:
            elapsed = int((time.time() - start_time) * 1000) if start_time else None
            error_details = traceback.format_exc()
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"HTTP 工具中发生意外错误: {str(e)}\n{error_details}")
            return {
                "error": error_msg,
                "error_details": error_details,
                "elapsed": elapsed,
                "ok": False
            }