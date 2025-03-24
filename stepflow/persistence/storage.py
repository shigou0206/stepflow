# stepflow/persistence/storage.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from stepflow.persistence.models import (
    Base, WorkflowDefinition, WorkflowInstance,
    StateExecution, ContextItem
)
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

DATABASE_URL = "sqlite:///./stepflow.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """
    初始化所有数据库表，在应用启动时调用一次
    """
    Base.metadata.create_all(bind=engine)

####################################################
# 1) WorkflowDefinition 部分
####################################################
def create_workflow_definition(dsl: dict,
                               name: Optional[str] = None,
                               version: Optional[str] = None) -> str:
    """
    创建一条 workflow_definition 记录，并返回 definition_id
    """
    session = SessionLocal()
    definition_id = str(uuid.uuid4())
    wf_def = WorkflowDefinition(
        definition_id=definition_id,
        name=name,
        version=version,
        dsl=dsl
    )
    session.add(wf_def)
    session.commit()
    session.close()
    return definition_id

def get_workflow_definition_by_id(definition_id: str) -> Optional[dict]:
    session = SessionLocal()
    wf_def = session.query(WorkflowDefinition).filter_by(definition_id=definition_id).first()
    session.close()
    if wf_def:
        return wf_def.dsl
    return None

def update_workflow_definition(definition_id: str,
                               dsl: Optional[dict] = None,
                               name: Optional[str] = None,
                               version: Optional[str] = None):
    session = SessionLocal()
    wf_def = session.query(WorkflowDefinition).filter_by(definition_id=definition_id).first()
    if wf_def:
        if dsl is not None:
            wf_def.dsl = dsl
        if name is not None:
            wf_def.name = name
        if version is not None:
            wf_def.version = version
        wf_def.updated_at = datetime.now()
        session.commit()
    session.close()

def delete_workflow_definition(definition_id: str):
    session = SessionLocal()
    session.query(WorkflowDefinition).filter_by(definition_id=definition_id).delete()
    session.commit()
    session.close()

####################################################
# 2) WorkflowInstance 部分
####################################################
def create_workflow_instance(dsl: dict,
                             initial_context: Optional[dict] = None) -> str:
    """
    创建一个 workflow instance：
      1) 先创建 workflow_definition 记录，并获得 definition_id
      2) 再创建 WorkflowInstance，将 definition_id 赋给 instance，
         同时保存初始上下文 (context) 和状态为 "CREATED"
    返回 instance_id
    """
    # 创建定义记录
    definition_id = create_workflow_definition(dsl)
    instance_id = str(uuid.uuid4())
    session = SessionLocal()
    instance = WorkflowInstance(
        instance_id=instance_id,
        definition_id=definition_id,
        # context=initial_context or {},
        status="CREATED"
    )
    session.add(instance)
    session.commit()
    session.close()
    return instance_id

def get_workflow_instance(instance_id: str) -> Optional[Dict[str, Any]]:
    session = SessionLocal()
    inst = session.query(WorkflowInstance).filter_by(instance_id=instance_id).first()
    if not inst:
        session.close()
        return None
    data = {
        "instance_id": inst.instance_id,
        "definition_id": inst.definition_id,
        "status": inst.status,
        "context": inst.context,
        "created_at": str(inst.created_at),
        "updated_at": str(inst.updated_at)
    }
    session.close()
    return data

def update_instance_status(instance_id: str,
                           status: str,
                           context: Dict[str, Any],
                           definition: Optional[dict] = None):
    """
    更新 WorkflowInstance 的状态和上下文。
    注意：在新设计中，definition 由 WorkflowDefinition 表管理，
    此处建议不要再传入 definition 参数；如果需要更新可额外调用 update_workflow_definition。
    """
    session = SessionLocal()
    inst = session.query(WorkflowInstance).filter_by(instance_id=instance_id).first()
    if inst:
        inst.status = status
        inst.context = context
        inst.updated_at = datetime.now()
        session.commit()
    session.close()

def get_workflow_context(instance_id: str) -> Dict[str, Any]:
    session = SessionLocal()
    inst = session.query(WorkflowInstance).filter_by(instance_id=instance_id).first()
    ctx = {}
    if inst and inst.context:
        ctx = inst.context
    session.close()
    return ctx

def list_workflow_instances() -> List[Dict[str, Any]]:
    session = SessionLocal()
    instances = session.query(WorkflowInstance).all()
    result = []
    for i in instances:
        result.append({
            "instance_id": i.instance_id,
            "definition_id": i.definition_id,
            "status": i.status,
            "context": i.context,
            "created_at": str(i.created_at),
            "updated_at": str(i.updated_at)
        })
    session.close()
    return result

def delete_workflow_instance(instance_id: str):
    session = SessionLocal()
    session.query(WorkflowInstance).filter_by(instance_id=instance_id).delete()
    session.commit()
    session.close()

# ####################################################
# # 3) WorkflowHistory 部分（如果不使用则可删除）
# ####################################################
# def save_state_history(instance_id: str,
#                        state_name: str,
#                        state_type: str,
#                        input_ctx: dict,
#                        output_ctx: dict,
#                        status: str,
#                        error_info: str,
#                        execution_time: float):
#     """
#     保存每个状态的执行历史记录
#     """
#     session = SessionLocal()
#     history_id = str(uuid.uuid4())
#     history = WorkflowHistory(
#         history_id=history_id,
#         instance_id=instance_id,
#         state_name=state_name,
#         state_type=state_type,
#         input_context=input_ctx,
#         output_context=output_ctx,
#         status=status,
#         error_info=error_info,
#         execution_time=execution_time
#     )
#     session.add(history)
#     session.commit()
#     session.close()

####################################################
# 4) StateExecution 部分
####################################################
def create_state_execution(instance_id: str,
                           state_name: str,
                           state_type: str,
                           input_data: dict,
                           status: str = "RUNNING",
                           retry_count: int = 0) -> str:
    session = SessionLocal()
    execution_id = str(uuid.uuid4())
    rec = StateExecution(
        execution_id=execution_id,
        instance_id=instance_id,
        state_name=state_name,
        state_type=state_type,
        status=status,
        input_data=input_data,
        retry_count=retry_count,
        start_time=datetime.now()
    )
    session.add(rec)
    session.commit()
    session.close()
    return execution_id

def update_state_execution(execution_id: str,
                           status: Optional[str] = None,
                           output_data: Optional[dict] = None,
                           execution_time: Optional[float] = None,
                           end_time: Optional[datetime] = None,
                           retry_count: Optional[int] = None):
    session = SessionLocal()
    rec = session.query(StateExecution).filter_by(execution_id=execution_id).first()
    if rec:
        if status:
            rec.status = status
        if output_data is not None:
            rec.output_data = output_data
        if execution_time is not None:
            rec.execution_time = execution_time
        if end_time is not None:
            rec.end_time = end_time
        if retry_count is not None:
            rec.retry_count = retry_count
        rec.updated_at = datetime.now()
        session.commit()
    session.close()

def get_state_execution(execution_id: str) -> Dict[str, Any]:
    session = SessionLocal()
    rec = session.query(StateExecution).filter_by(execution_id=execution_id).first()
    if not rec:
        session.close()
        return {}
    data = {
        "execution_id": rec.execution_id,
        "instance_id": rec.instance_id,
        "state_name": rec.state_name,
        "state_type": rec.state_type,
        "status": rec.status,
        "input_data": rec.input_data,
        "output_data": rec.output_data,
        "retry_count": rec.retry_count,
        "execution_time": rec.execution_time,
        "start_time": str(rec.start_time) if rec.start_time else None,
        "end_time": str(rec.end_time) if rec.end_time else None,
        "created_at": str(rec.created_at),
        "updated_at": str(rec.updated_at)
    }
    session.close()
    return data

def list_state_executions(instance_id: str) -> List[Dict[str, Any]]:
    session = SessionLocal()
    recs = session.query(StateExecution).filter_by(instance_id=instance_id).all()
    result = []
    for r in recs:
        result.append({
            "execution_id": r.execution_id,
            "state_name": r.state_name,
            "state_type": r.state_type,
            "status": r.status,
            "input_data": r.input_data,
            "output_data": r.output_data,
            "retry_count": r.retry_count,
            "execution_time": r.execution_time,
            "start_time": str(r.start_time) if r.start_time else None,
            "end_time": str(r.end_time) if r.end_time else None,
        })
    session.close()
    return result

####################################################
# 5) ContextItem 部分
####################################################
def create_context_item(instance_id: str, context_key: str, context_value: dict) -> str:
    session = SessionLocal()
    cid = str(uuid.uuid4())
    item = ContextItem(
        context_item_id=cid,
        instance_id=instance_id,
        context_key=context_key,
        context_value=context_value,
        updated_at=datetime.now()
    )
    session.add(item)
    session.commit()
    session.close()
    return cid

def update_context_item(item_id: str, context_value: dict):
    session = SessionLocal()
    item = session.query(ContextItem).filter_by(context_item_id=item_id).first()
    if item:
        item.context_value = context_value
        item.updated_at = datetime.now()
        session.commit()
    session.close()

def get_context_item(instance_id: str, context_key: str) -> Dict[str, Any]:
    session = SessionLocal()
    item = session.query(ContextItem).filter_by(instance_id=instance_id, context_key=context_key).first()
    val = {}
    if item and item.context_value:
        val = item.context_value
    session.close()
    return val

def list_context_items(instance_id: str) -> Dict[str, dict]:
    session = SessionLocal()
    items = session.query(ContextItem).filter_by(instance_id=instance_id).all()
    ret = {}
    for it in items:
        ret[it.context_key] = it.context_value
    session.close()
    return ret

def delete_context_item(item_id: str):
    session = SessionLocal()
    session.query(ContextItem).filter_by(context_item_id=item_id).delete()
    session.commit()
    session.close()