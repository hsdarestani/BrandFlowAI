from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as m
from app.database import Base
from app import tasks


def _session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'tasks.db'}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _seed(session_factory, provider="telegram"):
    with session_factory() as db:
        user = m.User(
            email="owner@example.com",
            password_hash="hashed",
            name="Owner",
            locale="en",
        )
        db.add(user)
        db.flush()
        org = m.Organization(
            name="Task Org",
            slug="task-org",
            mode="owner",
            owner_user_id=user.id,
        )
        db.add(org)
        db.flush()
        brand = m.Brand(
            organization_id=org.id,
            name="Task Brand",
            slug="task-brand",
            industry="software",
            country="DE",
            timezone="UTC",
            primary_language="en",
            description="",
            status="active",
        )
        db.add(brand)
        db.flush()
        account = m.ChannelAccount(
            brand_id=brand.id,
            provider=provider,
            account_name="Publishing channel",
            account_identifier="channel-1",
            connection_status="connected",
            capabilities_json={"can_publish": True},
            credentials_encrypted_json={"bot_token": "secret", "chat_id": "1"},
        )
        db.add(account)
        db.flush()
        draft = m.ContentDraft(
            brand_id=brand.id,
            channel=provider,
            content_type="post",
            language="en",
            title="Scheduled post",
            body="Publish me",
            status="scheduled",
            created_by_user_id=user.id,
        )
        db.add(draft)
        db.flush()
        scheduled = m.ScheduledPost(
            draft_id=draft.id,
            channel_account_id=account.id,
            scheduled_at=datetime.now(timezone.utc),
            status="scheduled",
        )
        db.add(scheduled)
        db.commit()
        return scheduled.id


def test_publish_scheduled_post_creates_one_publication(tmp_path, monkeypatch):
    sessions = _session_factory(tmp_path)
    post_id = _seed(sessions)

    class Connector:
        def publish_post(self, draft):
            assert draft.title == "Scheduled post"
            return {
                "status": "published",
                "provider_post_id": "provider-123",
                "public_url": "https://example.com/posts/provider-123",
            }

    monkeypatch.setattr(tasks, "SessionLocal", sessions)
    monkeypatch.setattr(tasks, "get_connector", lambda provider: Connector())

    result = tasks.publish_scheduled_post(post_id)
    assert result["status"] == "published"

    with sessions() as db:
        scheduled = db.get(m.ScheduledPost, post_id)
        assert scheduled.status == "published"
        assert scheduled.provider_post_id == "provider-123"
        assert db.query(m.PublishedPost).count() == 1
        assert db.get(m.ContentDraft, scheduled.draft_id).status == "published"

    second = tasks.publish_scheduled_post(post_id)
    assert second["status"] == "already_claimed"
    with sessions() as db:
        assert db.query(m.PublishedPost).count() == 1


def test_publish_failure_is_retried_with_persisted_error(tmp_path, monkeypatch):
    sessions = _session_factory(tmp_path)
    post_id = _seed(sessions)

    class BrokenConnector:
        def publish_post(self, draft):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(tasks, "SessionLocal", sessions)
    monkeypatch.setattr(tasks, "get_connector", lambda provider: BrokenConnector())

    result = tasks.publish_scheduled_post(post_id)
    assert result["status"] == "retry"
    assert result["retry_count"] == 1
    assert "provider unavailable" in result["error"]

    with sessions() as db:
        scheduled = db.get(m.ScheduledPost, post_id)
        assert scheduled.status == "retry"
        assert scheduled.retry_count == 1
        assert scheduled.scheduled_at > datetime.now(timezone.utc).replace(tzinfo=None)
        assert db.query(m.PublishedPost).count() == 0


def test_beat_runs_due_post_scan_every_minute():
    schedule = tasks.celery_app.conf.beat_schedule["publish-due-posts-every-minute"]
    assert schedule["task"] == "smarbiz.publish_due_posts"
    assert schedule["schedule"] == 60.0
