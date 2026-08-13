"""Remove unmistakable legacy mock/demo artifacts from production data.

Revision ID: 0004
Revises: 0003

Only rows that carry explicit old mock identifiers or the exact legacy calendar
placeholder signature are removed. User-created content is intentionally left
untouched.
"""

from alembic import op
from sqlalchemy import text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


MOCK_PROVIDER = "mock"
MOCK_POST_PREFIX = "mock-%"
LEGACY_TITLE_PATTERN = "Draft content idea %"
LEGACY_DESCRIPTION_PATTERN = "Draft weekly plan for %Review before publishing%"


def upgrade() -> None:
    bind = op.get_bind()

    # Use SQLAlchemy-bound parameters instead of embedding LIKE patterns directly
    # in driver SQL. Psycopg interprets raw percent signs as DBAPI placeholders,
    # which can make this migration fail before the API is able to start.
    bind.execute(
        text(
            """
            DELETE FROM insight_snapshots
            WHERE published_post_id IN (
                SELECT p.id
                FROM published_posts p
                LEFT JOIN channel_accounts c ON c.id = p.channel_account_id
                WHERE p.provider_post_id LIKE :mock_post_prefix
                   OR c.provider = :mock_provider
            )
            """
        ),
        {
            "mock_post_prefix": MOCK_POST_PREFIX,
            "mock_provider": MOCK_PROVIDER,
        },
    )
    bind.execute(
        text(
            """
            DELETE FROM published_posts
            WHERE provider_post_id LIKE :mock_post_prefix
               OR channel_account_id IN (
                   SELECT id FROM channel_accounts WHERE provider = :mock_provider
               )
            """
        ),
        {
            "mock_post_prefix": MOCK_POST_PREFIX,
            "mock_provider": MOCK_PROVIDER,
        },
    )
    bind.execute(
        text(
            """
            DELETE FROM scheduled_posts
            WHERE channel_account_id IN (
                SELECT id FROM channel_accounts WHERE provider = :mock_provider
            )
            """
        ),
        {"mock_provider": MOCK_PROVIDER},
    )
    bind.execute(
        text("DELETE FROM channel_accounts WHERE provider = :mock_provider"),
        {"mock_provider": MOCK_PROVIDER},
    )

    # Exact signature produced by the original hard-coded weekly loop.
    bind.execute(
        text(
            """
            DELETE FROM calendar_items
            WHERE title LIKE :legacy_title_pattern
              AND description LIKE :legacy_description_pattern
              AND status IN ('draft', 'idea', 'planned')
            """
        ),
        {
            "legacy_title_pattern": LEGACY_TITLE_PATTERN,
            "legacy_description_pattern": LEGACY_DESCRIPTION_PATTERN,
        },
    )


def downgrade() -> None:
    # Synthetic mock data is intentionally not recreated.
    pass
