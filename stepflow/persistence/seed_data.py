import asyncio
import json
from datetime import datetime

from stepflow.persistence.database import AsyncSessionLocal
from stepflow.persistence.models import WorkflowTemplate

async def seed_data():
    """填充初始数据"""
    print("填充初始数据...")
    
    async with AsyncSessionLocal() as session:
        # 检查是否已有数据
        from sqlalchemy import select
        result = await session.execute(select(WorkflowTemplate).limit(1))
        if result.first():
            print("数据库已有数据，跳过填充")
            return
        
        # 创建基本工作流模板
        templates = [
            WorkflowTemplate(
                template_id="simple-pass-workflow",
                name="Simple Pass Workflow",
                description="A simple workflow with a single Pass state",
                dsl_definition=json.dumps({
                    "Version": "1.0",
                    "Name": "SimplePassWorkflow",
                    "StartAt": "PassState",
                    "States": {
                        "PassState": {
                            "Type": "Pass",
                            "End": True
                        }
                    }
                }),
                updated_at=datetime.now()
            ),
            WorkflowTemplate(
                template_id="simple-task-workflow",
                name="Simple Task Workflow",
                description="A simple workflow with a single Task state",
                dsl_definition=json.dumps({
                    "Version": "1.0",
                    "Name": "SimpleTaskWorkflow",
                    "StartAt": "TaskState",
                    "States": {
                        "TaskState": {
                            "Type": "Task",
                            "ActivityType": "SimpleTask",
                            "End": True
                        }
                    }
                }),
                updated_at=datetime.now()
            )
        ]
        
        for template in templates:
            session.add(template)
        
        await session.commit()
        print(f"已创建 {len(templates)} 个工作流模板")

if __name__ == "__main__":
    asyncio.run(seed_data()) 