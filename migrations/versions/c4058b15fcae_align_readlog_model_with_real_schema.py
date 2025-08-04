"""Align ReadLog model with real schema

Revision ID: c4058b15fcae
Revises: fdaac43c659f
Create Date: 2025-08-03 01:07:19.469517
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c4058b15fcae'
down_revision = 'fdaac43c659f'
branch_labels = None
depends_on = None


def upgrade():
    # --- Keep password_hash as TEXT ---
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.TEXT(),
            type_=sa.TEXT(),  # ✅ Preserve TEXT
            existing_nullable=False
        )

    # --- Ensure read_logs has correct structure ---
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'read_logs' in tables:
        # Table exists, alter columns to match schema
        with op.batch_alter_table('read_logs', schema=None) as batch_op:
            batch_op.alter_column('update_id',
                                  existing_type=sa.VARCHAR(length=32),
                                  type_=sa.String(length=32),
                                  existing_nullable=False)
            batch_op.alter_column('user_id',
                                  existing_type=sa.INTEGER(),
                                  type_=sa.Integer(),
                                  existing_nullable=True)
            batch_op.alter_column('guest_name',
                                  existing_type=sa.VARCHAR(length=255),
                                  type_=sa.String(length=255),
                                  existing_nullable=True)
            batch_op.alter_column('timestamp',
                                  existing_type=postgresql.TIMESTAMP(),
                                  type_=sa.DateTime(),
                                  existing_nullable=False)
    else:
        # Table missing — create it
        op.create_table(
            'read_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('update_id', sa.String(length=32), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('guest_name', sa.String(length=255), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['update_id'], ['updates.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'])
        )


def downgrade():
    # --- Revert password_hash to VARCHAR(128) ---
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.TEXT(),
            type_=sa.String(length=128),
            existing_nullable=False
        )

    # --- Revert read_logs guest_name length to 100 ---
    with op.batch_alter_table('read_logs', schema=None) as batch_op:
        batch_op.alter_column('guest_name',
                              existing_type=sa.String(length=255),
                              type_=sa.String(length=100),
                              existing_nullable=True)
