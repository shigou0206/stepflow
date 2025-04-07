import asyncio
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from concurrent.futures import ThreadPoolExecutor

# 导入数据库
from stepflow.infrastructure.database import Base, async_engine

# 导入各个路由
from stepflow.interfaces.api.workflow_visibility_endpoints import router as vis_router
from stepflow.interfaces.api.workflow_execution_endpoints import router as exec_router
from stepflow.interfaces.api.workflow_template_endpoints import router as template_router
from stepflow.interfaces.api.workflow_event_endpoints import router as event_router
from stepflow.interfaces.api.activity_endpoints import router as activity_router
from stepflow.interfaces.api.timer_endpoints import router as timer_router

# 导入 Worker 协程函数
from stepflow.worker.activity_worker import run_activity_worker
from stepflow.worker.timer_worker import run_timer_worker

# 设置 logger
logger = logging.getLogger(__name__)

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    from stepflow.infrastructure.database import Base, async_engine
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 启动活动工作器
    workers = await start_activity_workers()
    app.state.workers = workers
    logger.info(f"已启动 {NUM_WORKERS} 个活动工作器")
    
    yield  # FastAPI 运行点
    
    # 关闭时停止工作器
    if hasattr(app.state, "workers"):
        for worker in app.state.workers:
            worker.cancel()
        
        # 等待所有工作器正常关闭
        await asyncio.gather(*app.state.workers, return_exceptions=True)
        logger.info("所有活动工作器已关闭")

# Create app with lifespan
app = FastAPI(title="StepFlow API", description="工作流执行引擎 API", lifespan=lifespan)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers for various endpoints
app.include_router(vis_router)
app.include_router(exec_router)
app.include_router(template_router)
app.include_router(event_router)
app.include_router(activity_router)
app.include_router(timer_router)

# 配置工作器数量
NUM_WORKERS = int(os.environ.get("NUM_ACTIVITY_WORKERS", "2"))

# 创建工作器启动函数
async def start_activity_workers():
    """启动多个活动工作器"""
    workers = []
    for i in range(NUM_WORKERS):
        worker = asyncio.create_task(run_activity_worker())
        workers.append(worker)
    
    return workers

@app.get("/")
async def root():
    """API 健康检查"""
    return {"message": "StepFlow API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)