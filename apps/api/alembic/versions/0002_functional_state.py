"""Persist workspace preferences and memory note state.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("settings_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("brand_memory_notes", sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.alter_column("organizations", "settings_json", server_default=None)
    op.alter_column("brand_memory_notes", "metadata_json", server_default=None)


def downgrade() -> None:
    op.drop_column("brand_memory_notes", "metadata_json")
    op.drop_column("organizations", "settings_json")
