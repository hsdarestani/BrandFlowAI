"""Initial Smarbiz schema.

Revision ID: 0001
Revises:

This revision must remain immutable. It intentionally uses the frozen schema
snapshot from the moment production migrations were introduced instead of the
live application model registry.
"""

from alembic import op

from app.initial_schema_v0001 import InitialBase

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    InitialBase.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    InitialBase.metadata.drop_all(bind=op.get_bind())
