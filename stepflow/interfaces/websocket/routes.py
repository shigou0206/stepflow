from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
import logging
from typing import Optional

from .connection_manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])
logger = logging.getLogger(__name__)

@router.websocket("/status")
async def websocket_status(
    websocket: WebSocket, 
    workflow_id: Optional[str] = Query(None)
):
    """WebSocket 端点，用于接收工作流状态更新"""
    await manager.connect(websocket, workflow_id)
    try:
        # 发送初始连接成功消息
        await websocket.send_json({
            "type": "connection_established",
            "workflow_id": workflow_id,
            "message": "WebSocket 连接已建立"
        })
        
        # 保持连接并处理客户端消息
        while True:
            # 接收客户端消息（可选）
            data = await websocket.receive_text()
            logger.debug(f"收到客户端消息: {data}")
            
            # 这里可以处理客户端发送的命令，如订阅特定工作流等
            
    except WebSocketDisconnect:
        # 客户端断开连接
        manager.disconnect(websocket, workflow_id)
    except Exception as e:
        logger.exception(f"WebSocket 错误: {str(e)}")
        manager.disconnect(websocket, workflow_id) 