# stepflow/infrastructure/models.py

import sqlalchemy
from sqlalchemy import (
    Column, String, Integer, Text, ForeignKey, DateTime, Boolean,
    Index, text
)
from sqlalchemy.orm import relationship
from .database import Base

# -----------------------
# workflow_templates
# -----------------------
class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    template_id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    dsl_definition = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


# -----------------------
# workflow_executions
# -----------------------
class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    __table_args__ = (
        # 声明索引 idx_wf_shard_status (shard_id, status)
        Index("idx_wf_shard_status", "shard_id", "status"),
    )

    run_id = Column(String(36), primary_key=True)
    workflow_id = Column(String(255), nullable=False)
    shard_id = Column(Integer, nullable=False)
    template_id = Column(String(36), ForeignKey("workflow_templates.template_id"))
    current_state_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    workflow_type = Column(String(255), nullable=False)
    input = Column(Text)           # JSON -> TEXT
    input_version = Column(Integer, nullable=False, server_default=text("1"))
    result = Column(Text)          # JSON -> TEXT
    result_version = Column(Integer, nullable=False, server_default=text("1"))
    start_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    close_time = Column(DateTime)
    current_event_id = Column(Integer, nullable=False, server_default=text("0"))
    memo = Column(Text)            # JSON -> TEXT
    search_attrs = Column(Text)    # JSON -> TEXT
    version = Column(Integer, nullable=False, server_default=text("1"))

    # optional relationship
    # template = relationship("WorkflowTemplate", backref="executions")


# -----------------------
# workflow_events
# -----------------------
class WorkflowEvent(Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        # 声明索引 idx_wf_events (run_id, event_id)
        # 声明索引 idx_wf_events_shard (shard_id, run_id, event_id)
        Index("idx_wf_events", "run_id", "event_id"),
        Index("idx_wf_events_shard", "shard_id", "run_id", "event_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)  # SERIAL -> autoincrement
    run_id = Column(String(36), nullable=False)
    shard_id = Column(Integer, nullable=False)
    event_id = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)
    attributes = Column(Text)      # JSON -> TEXT
    attr_version = Column(Integer, nullable=False, server_default=text("1"))
    timestamp = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    archived = Column(Boolean, nullable=False, server_default=text("0"))


# -----------------------
# timers
# -----------------------
class Timer(Base):
    __tablename__ = "timers"
    __table_args__ = (
        # 索引 idx_timers_run (run_id, fire_at)
        Index("idx_timers_run", "run_id", "fire_at"),
    )

    timer_id = Column(String(36), primary_key=True)
    run_id = Column(String(36), ForeignKey("workflow_executions.run_id"), nullable=False)
    shard_id = Column(Integer, nullable=False)
    fire_at = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False)
    version = Column(Integer, nullable=False, server_default=text("1"))


# -----------------------
# activity_tasks
# -----------------------
class ActivityTask(Base):
    __tablename__ = "activity_tasks"
    __table_args__ = (
        Index("idx_activity_run_seq", "run_id", "seq"),
        Index("idx_activity_status", "status"),
    )

    task_token = Column(String(36), primary_key=True)
    run_id = Column(String(36), ForeignKey("workflow_executions.run_id"), nullable=False)
    shard_id = Column(Integer, nullable=False)
    seq = Column(Integer, nullable=False, server_default=text("1"))
    activity_type = Column(String(255), nullable=False)
    input = Column(Text)           # JSON -> TEXT
    input_version = Column(Integer, nullable=False, server_default=text("1"))
    status = Column(String(50), nullable=False)
    result = Column(Text)          # JSON -> TEXT
    result_version = Column(Integer, nullable=False, server_default=text("1"))
    attempt = Column(Integer, nullable=False, server_default=text("1"))
    max_attempts = Column(Integer, nullable=False, server_default=text("3"))
    heartbeat_at = Column(DateTime)
    scheduled_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    timeout_seconds = Column(Integer)
    retry_policy = Column(Text)    # JSON -> TEXT
    version = Column(Integer, nullable=False, server_default=text("1"))


# -----------------------
# workflow_visibility
# -----------------------
class WorkflowVisibility(Base):
    __tablename__ = "workflow_visibility"
    __table_args__ = (
        Index("idx_visibility_status", "status"),
    )

    run_id = Column(String(36), primary_key=True)
    workflow_id = Column(String(255))
    workflow_type = Column(String(255))
    start_time = Column(DateTime)
    close_time = Column(DateTime)
    status = Column(String(50))
    memo = Column(Text)            # JSON -> TEXT
    search_attrs = Column(Text)    # JSON -> TEXT
    version = Column(Integer, nullable=False, server_default=text("1"))