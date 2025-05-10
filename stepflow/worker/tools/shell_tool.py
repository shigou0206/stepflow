import asyncio
import logging
from typing import Dict, Any
from .base_tool import ITool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # 设置日志级别为 INFO

class ShellTool(ITool):
    """Shell 命令执行工具"""
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Shell 命令
        
        参数:
        - command: 要执行的命令 (必需)
        - timeout: 超时时间（秒），默认 30 秒
        - shell: 是否使用 shell 执行，默认 True
        - cwd: 工作目录
        - env: 环境变量
        
        返回:
        - returncode: 命令返回码
        - stdout: 标准输出
        - stderr: 标准错误
        - success: 命令是否成功执行 (returncode == 0)
        """
        # 记录开始执行的日志
        logger.info(f"开始执行 Shell 命令")
        
        # 获取命令参数
        command = parameters.get("command")
        if not command:
            logger.error("Shell 命令缺少必需参数: command")
            return {
                "success": False,
                "error": "Missing required parameter: command"
            }
        
        # 获取其他可选参数
        timeout = parameters.get("timeout", 30)
        shell = parameters.get("shell", True)
        cwd = parameters.get("cwd")
        env = parameters.get("env")
        
        logger.info(f"执行 Shell 命令: {command}")
        logger.info(f"参数: timeout={timeout}, shell={shell}, cwd={cwd}")
        
        try:
            # 使用 asyncio 创建子进程
            if shell:
                # 使用 shell 执行命令
                logger.info("使用 shell 模式执行命令")
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env
                )
            else:
                # 不使用 shell 执行命令
                logger.info("使用非 shell 模式执行命令")
                process = await asyncio.create_subprocess_exec(
                    *command.split(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env
                )
            
            # 等待命令执行完成，设置超时
            try:
                logger.info(f"等待命令执行完成，超时时间: {timeout}秒")
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                
                # 解码输出
                stdout_str = stdout.decode()
                stderr_str = stderr.decode()
                
                # 记录命令执行结果
                logger.info(f"命令执行完成，返回码: {process.returncode}")
                if stdout_str:
                    logger.info(f"标准输出: {stdout_str[:200]}..." if len(stdout_str) > 200 else f"标准输出: {stdout_str}")
                if stderr_str:
                    logger.info(f"标准错误: {stderr_str[:200]}..." if len(stderr_str) > 200 else f"标准错误: {stderr_str}")
                
                # 返回结果
                return {
                    "returncode": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "success": process.returncode == 0
                }
            except asyncio.TimeoutError:
                # 超时处理
                logger.error(f"命令执行超时，超过 {timeout} 秒")
                try:
                    process.kill()
                    logger.info("已终止超时进程")
                except:
                    logger.error("终止超时进程失败")
                
                return {
                    "success": False,
                    "error": f"Command execution timed out after {timeout} seconds"
                }
                
        except Exception as e:
            logger.exception(f"Shell 命令执行失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }