"""Application settings loaded from environment variables (see .env.example)."""

from functools import lru_cache
from typing import Annotated

from pydantic import AnyHttpUrl, AnyUrl, PostgresDsn, UrlConstraints, field_validator
from pydantic_core import Url
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# pydantic has no built-in https-only URL type; build one so that a wrong
# scheme (Telegram requires https for Mini Apps and webhooks) fails at startup.
HttpsUrl = Annotated[Url, UrlConstraints(allowed_schemes=["https"], host_required=True)]


class Settings(BaseSettings):
    """Every component (API, bot) reads the same set of typed settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: PostgresDsn
    s3_endpoint_url: AnyHttpUrl
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str

    telegram_bot_token: str
    # Optional proxy for api.telegram.org (http://... or socks5://...), needed on networks
    # where Telegram is blocked.
    telegram_proxy_url: AnyUrl | None = None
    # Comma-separated Telegram user IDs, e.g. TELEGRAM_ADMIN_IDS=111111111,222222222
    telegram_admin_ids: Annotated[frozenset[int], NoDecode] = frozenset()
    # Telegram only opens https URLs inside Mini Apps.
    miniapp_url: HttpsUrl

    # Public base URL of this API; product image URLs are built from it.
    public_api_url: AnyHttpUrl

    # Empty TELEGRAM_WEBHOOK_URL means long polling (single instance).
    # Set it to enable webhook mode so several bot instances can run behind a load balancer.
    telegram_webhook_url: HttpsUrl | None = None
    telegram_webhook_secret: str | None = None
    webhook_server_port: int = 8080

    @field_validator("telegram_admin_ids", mode="before")
    @classmethod
    def split_admin_ids(cls, value: object) -> object:
        """Parse the raw env string into a list before pydantic coerces it to frozenset[int]."""
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
