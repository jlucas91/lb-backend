import uuid
from dataclasses import dataclass
from typing import Any

import aioboto3
from botocore.config import Config

from app.core.config import get_settings

session = aioboto3.Session()


@dataclass(frozen=True)
class ObjectMeta:
    content_type: str
    content_length: int


class S3StorageService:
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._region = settings.aws_region
        self._upload_expiry = settings.s3_upload_expiry
        self._download_expiry = settings.s3_download_expiry
        self._client_kwargs: dict[str, str] = {
            "region_name": settings.aws_region,
        }
        if settings.aws_access_key_id:
            self._client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            self._client_kwargs["aws_secret_access_key"] = (
                settings.aws_secret_access_key
            )

    def _s3_client(self) -> Any:
        return session.client(
            "s3",
            config=Config(signature_version="s3v4"),
            **self._client_kwargs,
        )

    def generate_storage_key(self, filename: str, prefix: str = "uploads") -> str:
        return f"{prefix}/{uuid.uuid4()}/{filename}"

    async def generate_upload_url(
        self, key: str, content_type: str, expires: int | None = None
    ) -> str:
        async with self._s3_client() as s3:
            url: str = await s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires or self._upload_expiry,
            )
        return url

    async def generate_download_url(self, key: str, expires: int | None = None) -> str:
        async with self._s3_client() as s3:
            url: str = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires or self._download_expiry,
            )
        return url

    async def upload_object(self, key: str, data: bytes, content_type: str) -> int:
        """Upload bytes directly to S3. Returns size in bytes."""
        async with self._s3_client() as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        return len(data)

    async def head_object(self, key: str) -> ObjectMeta:
        async with self._s3_client() as s3:
            resp = await s3.head_object(Bucket=self._bucket, Key=key)
        return ObjectMeta(
            content_type=resp["ContentType"],
            content_length=resp["ContentLength"],
        )

    async def delete_object(self, key: str) -> None:
        async with self._s3_client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=key)


def get_storage() -> S3StorageService:
    return S3StorageService()
