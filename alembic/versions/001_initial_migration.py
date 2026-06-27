"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-27 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # businesses
    op.create_table('businesses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('wa_phone_number_id', sa.String(), nullable=False),
        sa.Column('wa_access_token', sa.String(), nullable=False),
        sa.Column('sheets_id', sa.String(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_businesses_wa_phone_number_id'), 'businesses', ['wa_phone_number_id'], unique=True)

    # customers
    op.create_table('customers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_business_id'), 'customers', ['business_id'], unique=False)
    op.create_index(op.f('ix_customers_phone_number'), 'customers', ['phone_number'], unique=False)

    # conversations
    op.create_table('conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('last_interaction_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_customer_id'), 'conversations', ['customer_id'], unique=False)
    op.create_index(op.f('ix_conversations_session_id'), 'conversations', ['session_id'], unique=False)

    # messages
    op.create_table('messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', name='roleenum'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_table('messages')
    op.execute("DROP TYPE roleenum;")
    op.drop_index(op.f('ix_conversations_session_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_customer_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_customers_phone_number'), table_name='customers')
    op.drop_index(op.f('ix_customers_business_id'), table_name='customers')
    op.drop_table('customers')
    op.drop_index(op.f('ix_businesses_wa_phone_number_id'), table_name='businesses')
    op.drop_table('businesses')
