"""Add phase_type to devices table

Revision ID: add_phase_type
Revises: 
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_phase_type'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'devices',
        sa.Column('phase_type', sa.String(20), nullable=True)
    )
    # Add index for phase_type for faster queries
    op.create_index('ix_devices_phase_type', 'devices', ['phase_type'])


def downgrade() -> None:
    op.drop_index('ix_devices_phase_type', table_name='devices')
    op.drop_column('devices', 'phase_type')
