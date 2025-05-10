import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

ENV = os.getenv("STEPFLOW_ENV", "dev")

if ENV == "test":
    # 测试环境用异步SQLite内存库 或 stepflow_test.db
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    # 你也可改成文件形式 => "sqlite+aiosqlite:///stepflow_test.db"
else:
    # 开发或生产环境用 stepflow.db (异步)
    DATABASE_URL = "sqlite+aiosqlite:///stepflow.db"

# 重命名为 async_engine，方便外部导入
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 需要查看SQL可设True
    future=True,
    # 增加连接池大小
    pool_size=20,
    max_overflow=40,
    # 设置连接超时
    pool_timeout=30,
    # 启用连接池预热
    pool_pre_ping=True,
    # connect_args={"check_same_thread": False}, # aiosqlite时一般不必
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
    # 添加自动刷新
    autoflush=True
)

Base = declarative_base()

async def get_db_session():
    """
    在 FastAPI等框架中:
    from stepflow.infrastructure.database import get_db_session

    async def some_endpoint(db=Depends(get_db_session)):
        ...
    """
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

# 确保这个变量被定义
SQLALCHEMY_DATABASE_URL = "sqlite:///stepflow.db"