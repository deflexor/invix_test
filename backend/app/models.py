"""Pydantic models shared by the database layer and the HTTP API."""

from datetime import datetime

from pydantic import BaseModel


class Product(BaseModel):
    """Product as stored in PostgreSQL."""

    id: int
    name: str
    image_key: str
    created_at: datetime


class ProductOut(BaseModel):
    """Product as returned by the HTTP API."""

    id: int
    name: str
    image_url: str
    created_at: datetime
