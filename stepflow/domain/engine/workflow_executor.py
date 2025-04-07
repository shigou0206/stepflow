import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC

from stepflow.domain.dsl_model import WorkflowDSL
from stepflow.domain.engine.execution_engine import advance_workflow
from stepflow.infrastructure.models import WorkflowExecution
from stepflow.infrastructure.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# 添加一个信号量来限制并行执行的工作流数量
MAX_CONCURRENT_WORKFLOWS = 20
workflow_semaphore = asyncio.Semaphore(MAX_CONCURRENT_WORKFLOWS)

class WorkflowExecutor:
    """工作流执行器，负责执行单个工作流实例"""
    
    def __init__(self, run_id: str, dsl: WorkflowDSL, input_data: Dict[str, Any]):
        self.run_id = run_id
        self.dsl = dsl
        self.input_data = input_data
        self.current_state = None
        
    async def execute(self):
        """执行工作流"""
        async with workflow_semaphore:  # 使用信号量限制并行数量
            try:
                logger.info(f"开始执行工作流 {self.run_id}")
                
                # 获取起始状态
                start_state_name = self.dsl.start_at
                if not start_state_name or start_state_name not in self.dsl.states:
                    raise ValueError(f"无效的起始状态: {start_state_name}")
                
                # 执行工作流逻辑
                current_state_name = start_state_name
                current_data = self.input_data
                
                while True:
                    # 获取当前状态定义
                    state_def = self.dsl.states[current_state_name]
                    state_type = state_def.get("Type")
                    
                    logger.info(f"执行工作流 {self.run_id} 的状态 {current_state_name} (类型: {state_type})")
                    
                    # 根据状态类型执行不同的逻辑
                    if state_type == "Task":
                        current_data = await self.execute_task_state(current_state_name, state_def, current_data)
                    elif state_type == "Pass":
                        current_data = self.execute_pass_state(state_def, current_data)
                    elif state_type == "Choice":
                        next_state = self.execute_choice_state(state_def, current_data)
                        if next_state:
                            current_state_name = next_state
                            continue
                    elif state_type == "Wait":
                        # 处理等待状态
                        wait_time = await self.execute_wait_state(state_def, current_data)
                        if wait_time > 0:
                            # 如果需要等待，则暂停执行
                            logger.info(f"工作流 {self.run_id} 等待 {wait_time} 秒")
                            return
                    else:
                        raise ValueError(f"不支持的状态类型: {state_type}")
                    
                    # 检查是否是终止状态
                    if state_def.get("End", False):
                        logger.info(f"工作流 {self.run_id} 执行完成")
                        await self.complete_workflow(current_data)
                        return
                    
                    # 获取下一个状态
                    next_state = state_def.get("Next")
                    if not next_state:
                        raise ValueError(f"状态 {current_state_name} 没有指定下一个状态且不是终止状态")
                    
                    current_state_name = next_state
                
            except Exception as e:
                logger.exception(f"工作流 {self.run_id} 执行出错: {str(e)}")
                await self.fail_workflow(str(e))

# 添加一个工作流执行管理器来管理并行执行
class WorkflowExecutionManager:
    """工作流执行管理器，负责管理多个工作流的并行执行"""
    
    def __init__(self):
        self.running_workflows = {}
        
    async def start_workflow(self, run_id: str, dsl: WorkflowDSL, input_data: Dict[str, Any]):
        """启动一个新的工作流执行"""
        executor = WorkflowExecutor(run_id, dsl, input_data)
        
        # 将执行任务添加到事件循环中
        task = asyncio.create_task(executor.execute())
        self.running_workflows[run_id] = task
        
        # 添加回调以在完成时清理
        task.add_done_callback(lambda t: self.cleanup_workflow(run_id, t))
        
        return task
    
    def cleanup_workflow(self, run_id: str, task):
        """清理已完成的工作流"""
        if run_id in self.running_workflows:
            del self.running_workflows[run_id]
            
        # 检查任务是否有异常
        if task.done() and not task.cancelled():
            try:
                task.result()
            except Exception as e:
                logger.error(f"工作流 {run_id} 执行失败: {str(e)}")
    
    async def stop_workflow(self, run_id: str):
        """停止一个正在运行的工作流"""
        if run_id in self.running_workflows:
            task = self.running_workflows[run_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"工作流 {run_id} 已取消")
            
            del self.running_workflows[run_id]
            return True
        return False
    
    def get_running_workflows(self) -> List[str]:
        """获取所有正在运行的工作流ID"""
        return list(self.running_workflows.keys())

# 创建全局工作流执行管理器实例
workflow_manager = WorkflowExecutionManager() 