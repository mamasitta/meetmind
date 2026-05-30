"""remove_meeting_chunks_table

Revision ID: 19592703e2a1
Revises: eb98a2aca960
Create Date: 2026-05-30 17:52:19.426255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '19592703e2a1'
down_revision: Union[str, Sequence[str], None] = 'eb98a2aca960'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Drop foreign key constraints (if any)
    op.drop_constraint('meeting_chunks_meeting_id_fkey', 'meeting_chunks', type_='foreignkey')
    
    # 2. Drop the meeting_chunks table
    op.drop_table('meeting_chunks')
    
    # 3. Remove pgvector extension (optional - only if no other tables use it)
    # Check if other tables use vector type first
    op.execute('DROP EXTENSION IF EXISTS vector CASCADE')
    
    print("✅ Removed meeting_chunks table")


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Recreate pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # 2. Recreate meeting_chunks table
    op.create_table(
        'meeting_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('meeting_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('embedding', sa.Vector(1536), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # 2. Recreate foreign key
    op.create_foreign_key(
        'meeting_chunks_meeting_id_fkey',
        'meeting_chunks',
        'meetings',
        ['meeting_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    print("✅ Restored meeting_chunks table")
