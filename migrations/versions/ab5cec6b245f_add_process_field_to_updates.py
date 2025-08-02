"""Add process field to updates

Revision ID: ab5cec6b245f
Revises: 401d5ed58c1d
Create Date: 2025-08-02 10:11:36.584784
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab5cec6b245f'
down_revision = '401d5ed58c1d'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add column as nullable first
    with op.batch_alter_table('updates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('process', sa.String(length=32), nullable=True))

    # Step 2: Fill existing rows with default value
    op.execute("UPDATE updates SET process = 'ABC'")

    # Step 3: Alter column to make it non-nullable
    with op.batch_alter_table('updates', schema=None) as batch_op:
        batch_op.alter_column('process', nullable=False)

    # ✅ Ensure password_hash is TEXT
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=128),
            type_=sa.Text(),
            existing_nullable=False
        )


def downgrade():
    # Safely convert password_hash back to VARCHAR(128) by truncating if too long
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Use postgresql_using to avoid truncation error
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=128),
            existing_nullable=False,
            postgresql_using="left(password_hash, 128)"
        )

    with op.batch_alter_table('updates', schema=None) as batch_op:
        batch_op.drop_column('process')
