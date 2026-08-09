"""Remove unmistakable legacy mock/demo artifacts from production data.

Revision ID: 0004
Revises: 0003

Only rows that carry explicit old mock identifiers or the exact legacy calendar
placeholder signature are removed. User-created content is intentionally left
untouched.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Insight snapshots depend on PublishedPost, so remove snapshots first.
    bind.exec_driver_sql(
        """
        DELETE FROM insight_snapshots
        WHERE published_post_id IN (
            SELECT p.id
            FROM published_posts p
            LEFT JOIN channel_accounts c ON c.id = p.channel_account_id
            WHERE p.provider_post_id LIKE 'mock-%'
               OR c.provider = 'mock'
        )
        """
    )
    bind.exec_driver_sql(
        """
        DELETE FROM published_posts
        WHERE provider_post_id LIKE 'mock-%'
           OR channel_account_id IN (SELECT id FROM channel_accounts WHERE provider = 'mock')
        """
    )
    bind.exec_driver_sql(
        """
        DELETE FROM scheduled_posts
        WHERE channel_account_id IN (SELECT id FROM channel_accounts WHERE provider = 'mock')
        """
    )
    bind.exec_driver_sql("DELETE FROM channel_accounts WHERE provider = 'mock'")

    # Exact signature produced by the original hard-coded weekly loop.
    bind.exec_driver_sql(
        """
        DELETE FROM calendar_items
        WHERE title LIKE 'Draft content idea %'
          AND description LIKE 'Draft weekly plan for %Review before publishing%'
          AND status IN ('draft', 'idea', 'planned')
        """
    )


def downgrade() -> None:
    # Synthetic mock data is intentionally not recreated.
    pass
