"""Add last_result_url to scheduled_reports

Revision ID: 002_add_last_result_url
Revises: 001_initial
Create Date: 2026-02-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_add_last_result_url'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'scheduled_reports',
        sa.Column('last_result_url', sa.String(2000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('scheduled_reports', 'last_result_url')
