"""Smarbiz Celery beat scheduler process."""

from app.tasks import celery_app


if __name__ == "__main__":
    celery_app.start(
        [
            "beat",
            "--loglevel=INFO",
            "--pidfile=",
        ]
    )
