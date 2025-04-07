"""Initial migration

Revision ID: 99311c02d230
Revises: 51c903151a82
Create Date: 2025-04-07 20:55:48.735070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99311c02d230'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 创建 workflow_templates 表
    op.create_table(
        'workflow_templates',
        sa.Column('template_id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dsl_definition', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    )

    # 创建 workflow_executions 表
    op.create_table(
        'workflow_executions',
        sa.Column('run_id', sa.String(36), primary_key=True),
        sa.Column('workflow_id', sa.String(255), nullable=False),
        sa.Column('shard_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.String(36), sa.ForeignKey('workflow_templates.template_id')),
        sa.Column('current_state_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('workflow_type', sa.String(255), nullable=False),
        sa.Column('input', sa.Text(), nullable=True),
        sa.Column('input_version', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('result_version', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('start_time', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('close_time', sa.DateTime(), nullable=True),
        sa.Column('current_event_id', sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('search_attrs', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text("1"))
    )
    op.create_index('idx_wf_shard_status', 'workflow_executions', ['shard_id', 'status'])

    # 创建 workflow_events 表
    op.create_table(
        'workflow_events',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('shard_id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('attributes', sa.Text(), nullable=True),
        sa.Column('attr_version', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('archived', sa.Boolean(), nullable=False, server_default=sa.text("0"))
    )
    op.create_index('idx_wf_events', 'workflow_events', ['run_id', 'event_id'])
    op.create_index('idx_wf_events_shard', 'workflow_events', ['shard_id', 'run_id', 'event_id'])

    # 创建 timers 表
    op.create_table(
        'timers',
        sa.Column('timer_id', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('workflow_executions.run_id'), nullable=False),
        sa.Column('shard_id', sa.Integer(), nullable=False),
        sa.Column('fire_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text("1"))
    )
    op.create_index('idx_timers_run', 'timers', ['run_id', 'fire_at'])

    # 创建 activity_tasks 表
    op.create_table(
        'activity_tasks',
        sa.Column('task_token', sa.String(36), primary_key=True),
        sa.Column('run_id', sa.String(36), sa.ForeignKey('workflow_executions.run_id'), nullable=False),
        sa.Column('shard_id', sa.Integer(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('activity_type', sa.String(255), nullable=False),
        sa.Column('input', sa.Text(), nullable=True),
        sa.Column('input_version', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('result_version', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column('heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('retry_policy', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text("1"))
    )
    op.create_index('idx_activity_run_seq', 'activity_tasks', ['run_id', 'seq'])
    op.create_index('idx_activity_status', 'activity_tasks', ['status'])

    # 创建 workflow_visibility 表
    op.create_table(
        'workflow_visibility',
        sa.Column('run_id', sa.String(36), primary_key=True),
        sa.Column('workflow_id', sa.String(255), nullable=True),
        sa.Column('workflow_type', sa.String(255), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('close_time', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('memo', sa.Text(), nullable=True),
        sa.Column('search_attrs', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text("1"))
    )
    op.create_index('idx_visibility_status', 'workflow_visibility', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    # 删除表（按照依赖关系的相反顺序）
    op.drop_table('workflow_visibility')
    op.drop_table('activity_tasks')
    op.drop_table('timers')
    op.drop_table('workflow_events')
    op.drop_table('workflow_executions')
    op.drop_table('workflow_templates')
