import asyncio
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

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

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create background tasks
    activity_task = asyncio.create_task(run_activity_worker())
    timer_task = asyncio.create_task(run_timer_worker())
    
    yield  # This is where FastAPI runs
    
    # Shutdown: cancel tasks if needed
    activity_task.cancel()
    timer_task.cancel()

# Create app with lifespan
app = FastAPI(lifespan=lifespan)

# Include routers for various endpoints
app.include_router(vis_router)
app.include_router(exec_router)
app.include_router(template_router)
app.include_router(event_router)
app.include_router(activity_router)
app.include_router(timer_router)

@app.get("/")
async def root():
    return {"message": "Stepflow API & Worker combined service running."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)