from celery import Celery

from app.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()

    app = Celery("locationsbook")
    app.conf.update(
        broker_url=settings.celery_broker_url,
        broker_transport_options={
            "region": settings.aws_region,
            "visibility_timeout": settings.celery_task_visibility_timeout,
            "wait_time_seconds": 20,  # SQS long polling
        },
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        result_backend=None,
        task_ignore_result=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_default_queue=settings.celery_queue_name,
    )
    app.autodiscover_tasks(["app.tasks"])
    return app


celery_app = create_celery_app()
