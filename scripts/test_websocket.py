#!/usr/bin/env python
# scripts/test_websocket.py

import asyncio
import websockets
import json
import sys

async def test_websocket(workflow_id=None):
    """测试 WebSocket 连接"""
    # 构建 WebSocket URL
    base_url = "ws://localhost:8000/ws/status"
    if workflow_id:
        url = f"{base_url}?workflow_id={workflow_id}"
        print(f"连接到工作流 {workflow_id} 的 WebSocket...")
    else:
        url = base_url
        print("连接到全局 WebSocket...")
    
    try:
        async with websockets.connect(url) as websocket:
            print("WebSocket 连接已建立")
            
            # 接收初始连接消息
            response = await websocket.recv()
            print(f"收到消息: {response}")
            
            # 保持连接并接收消息
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"收到更新: {json.dumps(data, indent=2)}")
                except websockets.exceptions.ConnectionClosed:
                    print("连接已关闭")
                    break
    except Exception as e:
        print(f"WebSocket 错误: {str(e)}")

if __name__ == "__main__":
    # 可以通过命令行参数指定工作流 ID
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    asyncio.run(test_websocket(workflow_id)) 