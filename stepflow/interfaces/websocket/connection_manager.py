import json
import logging
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    """管理 WebSocket 连接"""
    
    def __init__(self):
        # 所有活跃连接
        self.active_connections: List[WebSocket] = []
        # 按工作流 ID 分组的连接
        self.workflow_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, workflow_id: Optional[str] = None):
        """建立新的 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # 如果指定了工作流 ID，将连接添加到对应组
        if workflow_id:
            if workflow_id not in self.workflow_connections:
                self.workflow_connections[workflow_id] = []
            self.workflow_connections[workflow_id].append(websocket)
            logger.info(f"WebSocket 连接已建立，关联工作流: {workflow_id}")
        else:
            logger.info("WebSocket 连接已建立 (全局)")
    
    def disconnect(self, websocket: WebSocket, workflow_id: Optional[str] = None):
        """断开 WebSocket 连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 从工作流组中移除
        if workflow_id and workflow_id in self.workflow_connections:
            if websocket in self.workflow_connections[workflow_id]:
                self.workflow_connections[workflow_id].remove(websocket)
            # 如果组为空，删除该组
            if not self.workflow_connections[workflow_id]:
                del self.workflow_connections[workflow_id]
            logger.info(f"WebSocket 连接已断开，工作流: {workflow_id}")
        else:
            # 检查所有工作流组，移除断开的连接
            for wf_id, connections in list(self.workflow_connections.items()):
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:
                        del self.workflow_connections[wf_id]
            logger.info("WebSocket 连接已断开 (全局)")
    
    async def broadcast(self, message: Any):
        """向所有连接广播消息"""
        if not self.active_connections:
            return
            
        # 将消息转换为 JSON 字符串
        if not isinstance(message, str):
            message = json.dumps(message)
            
        # 发送消息，忽略断开的连接
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"发送消息失败: {str(e)}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)
    
    async def send_to_workflow(self, workflow_id: str, message: Any):
        """向特定工作流的所有连接发送消息"""
        if workflow_id not in self.workflow_connections:
            return
            
        # 将消息转换为 JSON 字符串
        if not isinstance(message, str):
            message = json.dumps(message)
            
        # 发送消息，忽略断开的连接
        disconnected = []
        for connection in self.workflow_connections[workflow_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"发送消息到工作流 {workflow_id} 失败: {str(e)}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection, workflow_id)

# 创建全局连接管理器实例
manager = ConnectionManager() 