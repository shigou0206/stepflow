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
        # 添加超时处理
        async with websockets.connect(url, ping_interval=None, close_timeout=10) as websocket:
            print("WebSocket 连接已建立")
            
            # 接收初始连接消息
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"收到消息: {response}")
            
            # 保持连接并接收消息
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(message)
                    print(f"收到更新: {json.dumps(data, indent=2)}")
                except asyncio.TimeoutError:
                    print("等待消息超时，发送 ping...")
                    await websocket.ping()
                except websockets.exceptions.ConnectionClosed:
                    print("连接已关闭")
                    break
    except ConnectionRefusedError:
        print("连接被拒绝，请确保服务器正在运行")
    except asyncio.TimeoutError:
        print("连接或接收消息超时")
    except Exception as e:
        print(f"WebSocket 错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 可以通过命令行参数指定工作流 ID
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        asyncio.run(test_websocket(workflow_id))
    except KeyboardInterrupt:
        print("测试被用户中断") 