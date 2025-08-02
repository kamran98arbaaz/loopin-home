"""Make password_hash text

Revision ID: 401d5ed58c1d
Revises: 034bd85c9b44
Create Date: 2025-08-02 09:51:38.588708

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '401d5ed58c1d'
down_revision = '034bd85c9b44'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=128),
            type_=sa.Text(),
            existing_nullable=False,
        )

def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.Text(),
            type_=sa.String(length=128),
            existing_nullable=False,
        )


def upgrade():
    pass


def downgrade():
    pass
