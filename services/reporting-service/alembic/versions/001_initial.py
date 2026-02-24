"""Initial migration - create energy_reports, scheduled_reports, tenant_tariffs tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'energy_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('report_type', sa.Enum('consumption', 'comparison', name='reporttype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='reportstatus'), nullable=False),
        sa.Column('params', sa.JSON(), nullable=False),
        sa.Column('computation_mode', sa.Enum('direct_power', 'derived_single', 'derived_three', name='computationmode'), nullable=True),
        sa.Column('phase_type_used', sa.String(20), nullable=True),
        sa.Column('result_json', sa.JSON(), nullable=True),
        sa.Column('s3_key', sa.String(500), nullable=True),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_id')
    )
    op.create_index('ix_energy_reports_tenant_id', 'energy_reports', ['tenant_id'])
    op.create_index('ix_energy_reports_tenant_status', 'energy_reports', ['tenant_id', 'status'])
    op.create_index('ix_energy_reports_tenant_type_created', 'energy_reports', ['tenant_id', 'report_type', 'created_at'])

    op.create_table(
        'scheduled_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('schedule_id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('report_type', sa.Enum('consumption', 'comparison', name='scheduledreporttype'), nullable=False),
        sa.Column('frequency', sa.Enum('daily', 'weekly', 'monthly', name='scheduledfrequency'), nullable=False),
        sa.Column('params_template', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(50), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schedule_id')
    )
    op.create_index('ix_scheduled_reports_tenant_id', 'scheduled_reports', ['tenant_id'])

    op.create_table(
        'tenant_tariffs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False),
        sa.Column('energy_rate_per_kwh', sa.Float(), nullable=False),
        sa.Column('demand_charge_per_kw', sa.Float(), nullable=False, server_default='0'),
        sa.Column('reactive_penalty_rate', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fixed_monthly_charge', sa.Float(), nullable=False, server_default='0'),
        sa.Column('power_factor_threshold', sa.Float(), nullable=False, server_default='0.90'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id')
    )


def downgrade() -> None:
    op.drop_table('tenant_tariffs')
    op.drop_table('scheduled_reports')
    op.drop_table('energy_reports')
    op.execute('DROP TYPE IF EXISTS reporttype')
    op.execute('DROP TYPE IF EXISTS reportstatus')
    op.execute('DROP TYPE IF EXISTS computationmode')
    op.execute('DROP TYPE IF EXISTS scheduledreporttype')
    op.execute('DROP TYPE IF EXISTS scheduledfrequency')
