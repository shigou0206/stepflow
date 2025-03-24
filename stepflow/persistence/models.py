# stepflow/persistence/models.py

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, String, DateTime, JSON, Float,
    ForeignKey, Integer, func
)
from sqlalchemy.orm import relationship

Base = declarative_base()

class WorkflowDefinition(Base):
    """
    用来存储工作流定义 (DSL + 元信息), 
    多个 WorkflowInstance 可共享同一个 definition_id.
    """
    __tablename__ = "workflow_definition"

    definition_id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    version = Column(String, nullable=True)
    dsl = Column(JSON, nullable=False)  # Step Functions DSL (or其他DSL) 
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # 关系: 一个 definition 可以有多个 instance
    instances = relationship("WorkflowInstance", back_populates="definition")


class WorkflowInstance(Base):
    """
    工作流实例, 运行时上下文/状态等. 
    引用 WorkflowDefinition (definition_id) 
    """
    __tablename__ = "workflow_instance"

    instance_id = Column(String, primary_key=True)
    definition_id = Column(
        String,
        ForeignKey("workflow_definition.definition_id"),
        nullable=False
    )
    status = Column(String, nullable=True)     # RUNNING / COMPLETED / FAILED
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # 若上下文不大或更新不频繁, 可直接放这里:
    # context = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # 关系: 指回 definition
    definition = relationship("WorkflowDefinition", back_populates="instances")

    # 关系: 1个workflow_instance 对应多个 state执行
    states = relationship("StateExecution", back_populates="instance")

    # 若需要 context_item
    context_items = relationship("ContextItem", back_populates="instance")


class StateExecution(Base):
    """
    记录每个状态 / 节点执行的信息(输入/输出/耗时/状态).
    一个 workflow_instance可对应多条state执行(含重试).
    """
    __tablename__ = "state_execution"

    execution_id = Column(String, primary_key=True)
    instance_id = Column(
        String,
        ForeignKey("workflow_instance.instance_id"),
        nullable=False
    )
    state_name = Column(String, nullable=False)
    state_type = Column(String, nullable=True)   # Task / Choice / Map / Parallel / ...
    status = Column(String, nullable=True)       # e.g. "RUNNING"/"SUCCEEDED"/"FAILED"
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0)
    execution_time = Column(Float, nullable=True)

    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # 关系: 指回 workflow_instance
    instance = relationship("WorkflowInstance", back_populates="states")


class ContextItem(Base):
    """
    可选表, 当需要将上下文拆分为多个key => JSON
    适合上下文巨大or需要频繁局部更新. 
    如果不需要则可省略
    """
    __tablename__ = "context_item"

    context_item_id = Column(String, primary_key=True)
    instance_id = Column(
        String,
        ForeignKey("workflow_instance.instance_id"),
        nullable=False
    )
    context_key = Column(String, nullable=False)
    context_value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # 关系: 指回 instance
    instance = relationship("WorkflowInstance", back_populates="context_items")