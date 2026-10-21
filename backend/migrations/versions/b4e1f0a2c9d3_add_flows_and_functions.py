"""add flows and functions

Revision ID: b4e1f0a2c9d3
Revises: 97c3d7c7b8d2
Create Date: 2026-10-14 12:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4e1f0a2c9d3"
down_revision = "97c3d7c7b8d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "flows",
        sa.Column("template", sa.String(), nullable=False),
        sa.Column("flow_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("template"),
    )
    op.create_table(
        "functions",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("function_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade():
    op.drop_table("functions")
    op.drop_table("flows")
