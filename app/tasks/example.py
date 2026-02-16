import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def add(x: int, y: int) -> int:
    result = x + y
    logger.info("add(%s, %s) = %s", x, y, result)
    return result


@celery_app.task
def ping() -> str:
    logger.info("ping received — sending pong")
    return "pong"
