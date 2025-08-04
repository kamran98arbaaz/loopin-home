"""Test detection after restructure

Revision ID: 6de6914e9a76
Revises: c4058b15fcae
Create Date: 2025-08-03 02:37:10.098878
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6de6914e9a76'
down_revision = 'c4058b15fcae'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns with correct defaults
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column('role', sa.String(length=20), nullable=False, server_default='user'))
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=80),
               existing_nullable=False)
        batch_op.create_unique_constraint(None, ['email'])

    # Remove the server_default now that existing rows are filled
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.alter_column('username',
               existing_type=sa.String(length=80),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)
        batch_op.drop_column('role')
        batch_op.drop_column('email')
