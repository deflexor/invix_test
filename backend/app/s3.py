"""MinIO S3 helpers.
"""

import asyncio
import io
from urllib.parse import urlsplit

from minio import Minio

from app.config import Settings

IMAGE_CONTENT_TYPE = "image/jpeg"


def create_client(settings: Settings) -> Minio:
    url = urlsplit(str(settings.s3_endpoint_url))
    host = url.hostname
    if host is None:
        raise ValueError(f"S3_ENDPOINT_URL has no host: {settings.s3_endpoint_url}")
    endpoint = f"{host}:{url.port}" if url.port is not None else host
    return Minio(
        endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=url.scheme == "https",
    )


def _upload(client: Minio, bucket: str, key: str, data: bytes) -> None:
    client.put_object(bucket, key, io.BytesIO(data), len(data), content_type=IMAGE_CONTENT_TYPE)


async def upload_image(client: Minio, bucket: str, key: str, data: bytes) -> None:
    await asyncio.to_thread(_upload, client, bucket, key, data)


def _download(client: Minio, bucket: str, key: str) -> bytes:
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def download_image(client: Minio, bucket: str, key: str) -> bytes:
    return await asyncio.to_thread(_download, client, bucket, key)
