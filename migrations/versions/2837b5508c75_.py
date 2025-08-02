"""initial schema

Revision ID: 2837b5508c75
Revises: 
Create Date: 2025-08-02 00:07:15.916734
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2837b5508c75'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.VARCHAR(length=36), nullable=False),
        sa.Column('name', sa.VARCHAR(length=100), nullable=False),
        sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'updates',
        sa.Column('id', sa.VARCHAR(length=32), nullable=False),
        sa.Column('name', sa.VARCHAR(length=100), nullable=False),
        sa.Column('message', sa.TEXT(), nullable=False),
        sa.Column('timestamp', postgresql.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('updates')
    op.drop_table('users')
