# stepflow/persistence/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, JSON, Float, DateTime
from sqlalchemy.sql import func

Base = declarative_base()

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    instance_id = Column(String, primary_key=True)
    definition = Column(JSON)
    context = Column(JSON)
    status = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class WorkflowHistory(Base):
    __tablename__ = "workflow_history"

    history_id = Column(String, primary_key=True)
    instance_id = Column(String)
    state_name = Column(String)
    state_type = Column(String)
    input_context = Column(JSON)
    output_context = Column(JSON)
    status = Column(String)
    error_info = Column(String)
    execution_time = Column(Float)
    executed_at = Column(DateTime, server_default=func.now())