"""Add new user constraints or fields

Revision ID: fdaac43c659f
Revises: ab5cec6b245f
Create Date: 2025-08-02 11:13:41.683080

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fdaac43c659f'
down_revision = 'ab5cec6b245f'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add display_name nullable
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('display_name', sa.String(length=80), nullable=True))

    # 2. Backfill existing rows from username
    op.execute("UPDATE users SET display_name = username")

    # 3. Make display_name non-nullable
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('display_name', nullable=False)
    # Note: we intentionally do NOT change password_hash here; keep it as TEXT


def downgrade():
    # Remove display_name
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('display_name')
    # password_hash stays as TEXT (no downgrade needed for it here)
