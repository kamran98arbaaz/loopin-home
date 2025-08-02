"""Add role column manually

Revision ID: a05e9709e3ef
Revises: 2837b5508c75
Create Date: 2025-08-02 01:10:57.988857

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a05e9709e3ef'
down_revision = '2837b5508c75'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

def upgrade():
    op.add_column('users', sa.Column('role', sa.String(length=32), nullable=True))

def downgrade():
    op.drop_column('users', 'role')
