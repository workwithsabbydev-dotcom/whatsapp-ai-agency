"""Add human handoff to conversation

Revision ID: 002_human_handoff
Revises: 001_initial
Create Date: 2026-06-27 18:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_human_handoff'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('conversations', sa.Column('requires_human', sa.Boolean(), server_default='false', nullable=False))

def downgrade() -> None:
    op.drop_column('conversations', 'requires_human')
