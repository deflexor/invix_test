"""FastAPI application: read-only catalog API.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from minio import Minio
from minio.error import S3Error

from app import db, s3
from app.config import get_settings
from app.models import Product, ProductOut


def _to_product_out(product: Product) -> ProductOut:
    base_url = str(get_settings().public_api_url).rstrip("/")
    return ProductOut(
        id=product.id,
        name=product.name,
        image_url=f"{base_url}/api/products/{product.id}/image",
        created_at=product.created_at,
    )


def get_db_pool(request: Request) -> asyncpg.Pool:
    pool: asyncpg.Pool = request.app.state.db_pool
    return pool


def get_storage_client(request: Request) -> Minio:
    client: Minio = request.app.state.storage_client
    return client


DbPool = Annotated[asyncpg.Pool, Depends(get_db_pool)]
StorageClient = Annotated[Minio, Depends(get_storage_client)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.db_pool = await db.create_pool(settings)
    app.state.storage_client = s3.create_client(settings)
    yield
    await app.state.db_pool.close()


app = FastAPI(title="Catalog API", lifespan=lifespan)


@app.get("/api/products", response_model=list[ProductOut])
async def list_products(pool: DbPool) -> list[ProductOut]:
    products = await db.list_products(pool)
    return [_to_product_out(product) for product in products]


@app.get("/api/products/{product_id}/image")
async def get_product_image(
    product_id: int, pool: DbPool, storage_client: StorageClient
) -> Response:
    product = await db.get_product(pool, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        image = await s3.download_image(storage_client, get_settings().s3_bucket, product.image_key)
    except S3Error as error:
        raise HTTPException(status_code=404, detail="Product image not found") from error
    return Response(content=image, media_type=s3.IMAGE_CONTENT_TYPE)
