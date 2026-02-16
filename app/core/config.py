from functools import lru_cache

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

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
