# stepflow/persistence/storage.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from stepflow.persistence.models import Base, WorkflowInstance, WorkflowHistory
import uuid

DATABASE_URL = "sqlite:///./stepflow.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_workflow_definition(definition: dict, workflow_id: str = None):
    session = SessionLocal()
    if not workflow_id:
        workflow_id = str(uuid.uuid4())

    instance = session.query(WorkflowInstance).filter_by(instance_id=workflow_id).first()
    if not instance:
        instance = WorkflowInstance(
            instance_id=workflow_id,
            definition=definition,
            context={},
            status="CREATED"
        )
        session.add(instance)
    else:
        instance.definition = definition
    session.commit()
    session.close()
    return workflow_id

def get_workflow_definition(workflow_id: str):
    session = SessionLocal()
    instance = session.query(WorkflowInstance).filter_by(instance_id=workflow_id).first()
    session.close()
    return instance.definition if instance else None

def update_instance_status(instance_id: str, status: str, context: dict, definition: dict=None):
    session = SessionLocal()
    instance = session.query(WorkflowInstance).filter_by(instance_id=instance_id).first()
    if instance:
        instance.status = status
        instance.context = context
        if definition:
            instance.definition = definition
        session.commit()
    session.close()

def save_state_history(instance_id: str, state_name: str, state_type: str,
                       input_ctx: dict, output_ctx: dict,
                       status: str, error_info: str, execution_time: float):
    session = SessionLocal()
    history_id = str(uuid.uuid4())
    history = WorkflowHistory(
        history_id=history_id,
        instance_id=instance_id,
        state_name=state_name,
        state_type=state_type,
        input_context=input_ctx,
        output_context=output_ctx,
        status=status,
        error_info=error_info,
        execution_time=execution_time
    )
    session.add(history)
    session.commit()
    session.close()