# main.py
import uvicorn
from fastapi import FastAPI
from stepflow.api.routes import router as api_router
from stepflow.persistence.storage import init_db

app = FastAPI(
    title="StepFlow",
    version="0.1.0",
    description="A Step Functions-like workflow engine with FastAPI",
)

# 挂载路由
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
def on_startup():
    # 初始化数据库, 建表等
    init_db()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)