"""Smarbiz Celery worker process."""

from app.tasks import celery_app


if __name__ == "__main__":
    celery_app.worker_main(
        [
            "worker",
            "--loglevel=INFO",
            "--concurrency=2",
            "--hostname=smarbiz-worker@%h",
        ]
    )
