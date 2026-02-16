from functools import lru_cache
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/locationsbook"
    )
    app_env: str = "development"
    debug: bool = False
    app_name: str = "LocationsBook"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "locationsbook-dev"
    s3_upload_expiry: int = 300
    s3_download_expiry: int = 3600

    # Celery / SQS
    celery_broker_url: str = ""
    celery_queue_name: str = "locationsbook-default"
    celery_task_visibility_timeout: int = 1800  # 30 min

    model_config = {"env_file": ".env"}

    @model_validator(mode="after")
    def _reject_default_secret_key(self) -> "Settings":
        if (
            self.app_env != "development"
            and self.secret_key == "change-me-in-production"
        ):
            msg = (
                "SECRET_KEY must be set to a strong random value"
                " in non-development environments"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _build_celery_broker_url(self) -> "Settings":
        if not self.celery_broker_url:
            if self.aws_access_key_id and self.aws_secret_access_key:
                key = quote(self.aws_access_key_id, safe="")
                secret = quote(self.aws_secret_access_key, safe="")
                self.celery_broker_url = f"sqs://{key}:{secret}@"
            else:
                # ECS with IAM role — no explicit credentials needed
                self.celery_broker_url = "sqs://"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
