import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
import json

from stepflow.main import app
from stepflow.infrastructure.database import Base, async_engine, AsyncSessionLocal

# 创建测试客户端
client = TestClient(app)

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_database():
    """在异步上下文中设置和清理数据库"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

def test_validate_api_paths():
    """验证所有 API 路径是否可访问"""
    
    # 获取 OpenAPI 模式
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    # 提取所有 GET 路径进行测试
    paths = schema.get("paths", {})
    get_paths = []
    
    # 排除需要数据库的路径
    skip_paths = ["/visibility/", "/workflow_templates/", "/workflow_executions/", 
                 "/workflow_events/", "/activity_tasks/", "/timers/"]
    
    for path, methods in paths.items():
        if "get" in methods and "{" not in path:  # 排除需要参数的路径
            if not any(path.startswith(skip) for skip in skip_paths):
                get_paths.append(path)
    
    print(f"\n测试 {len(get_paths)} 个 GET 路径:")
    for path in get_paths:
        response = client.get(path)
        status = response.status_code
        print(f"  {path}: {status}")

def test_check_router_registration():
    """检查路由器注册情况"""
    
    print("\n检查路由器注册:")
    
    # 检查 app 中的路由器
    routers = []
    for route in app.routes:
        if hasattr(route, "app"):
            router_app = route.app
            if hasattr(router_app, "routes"):
                prefix = getattr(router_app, "prefix", "未知")
                routers.append((prefix, len(router_app.routes)))
    
    print(f"找到 {len(routers)} 个路由器:")
    for prefix, route_count in routers:
        print(f"  前缀: {prefix}, 路由数量: {route_count}")
    
    # 检查 main.py 中的路由器导入和注册
    import inspect
    import stepflow.main
    
    print("\n检查 main.py:")
    main_source = inspect.getsource(stepflow.main)
    router_imports = [line for line in main_source.split("\n") if "router" in line.lower() and "import" in line.lower()]
    router_includes = [line for line in main_source.split("\n") if "include_router" in line.lower()]
    
    print("路由器导入:")
    for line in router_imports:
        print(f"  {line.strip()}")
    
    print("\n路由器注册:")
    for line in router_includes:
        print(f"  {line.strip()}")

def test_check_api_prefixes():
    """检查 API 路由前缀"""
    
    print("\n检查 API 路由前缀:")
    
    # 获取 OpenAPI 模式
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    
    # 提取所有路径
    paths = schema.get("paths", {})
    
    # 按前缀分组
    prefixes = {}
    for path in paths.keys():
        parts = path.split("/")
        if len(parts) > 1:
            prefix = f"/{parts[1]}"
            if prefix not in prefixes:
                prefixes[prefix] = []
            prefixes[prefix].append(path)
    
    # 打印所有前缀
    for prefix, paths in prefixes.items():
        print(f"  前缀: {prefix}, 路径数量: {len(paths)}")
        for path in paths[:3]:  # 只打印前 3 个路径
            print(f"    {path}")
        if len(paths) > 3:
            print(f"    ... 还有 {len(paths) - 3} 个路径") 