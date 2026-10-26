"""PostgreSQL data access (asyncpg).
"""

import asyncpg

from app.config import Settings
from app.models import Product

_SELECT_COLUMNS = "id, name, image_key, created_at"


def _to_product(record: asyncpg.Record) -> Product:
    return Product.model_validate(dict(record))


async def create_pool(settings: Settings) -> asyncpg.Pool:
    """statement_cache_size=0 keeps the pool compatible with transaction-mode poolers (Supabase).

    A small pool (min_size=1, max_size=5) leaves pooler client slots for other instances.
    """
    return await asyncpg.create_pool(
        settings.database_url.unicode_string(),
        statement_cache_size=0,
        min_size=1,
        max_size=5,
        # Discard idle connections instead of handing out ones the network has dropped.
        max_inactive_connection_lifetime=60,
    )


async def insert_product(pool: asyncpg.Pool, name: str, image_key: str) -> Product:
    record = await pool.fetchrow(
        f"INSERT INTO products (name, image_key) VALUES ($1, $2) RETURNING {_SELECT_COLUMNS}",
        name,
        image_key,
    )
    if record is None:
        raise RuntimeError("INSERT INTO products did not return a row")
    return _to_product(record)


async def list_products(pool: asyncpg.Pool) -> list[Product]:
    records = await pool.fetch(
        f"SELECT {_SELECT_COLUMNS} FROM products ORDER BY created_at DESC, id DESC"
    )
    return [_to_product(record) for record in records]


async def get_product(pool: asyncpg.Pool, product_id: int) -> Product | None:
    record = await pool.fetchrow(
        f"SELECT {_SELECT_COLUMNS} FROM products WHERE id = $1", product_id
    )
    if record is None:
        return None
    return _to_product(record)
