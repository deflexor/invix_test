"""Telegram bot entrypoint: `uv run python -m app.bot`.
"""

import asyncio
import io
import logging

import asyncpg
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from minio import Minio

from app import db, s3
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

CATALOG_TEXT = "У меня есть товар"
CREATE_PRODUCT_INSTRUCTIONS = (
    "Отправьте название и фото одним сообщением: подпись к фото станет названием товара."
)
WEBHOOK_PATH = "/telegram/webhook"

router = Router(name="catalog")


def catalog_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть каталог", web_app=WebAppInfo(url=str(settings.miniapp_url))
                )
            ]
        ]
    )


async def answer_with_catalog(message: Message, settings: Settings) -> None:
    await message.answer(CATALOG_TEXT, reply_markup=catalog_keyboard(settings))


def is_admin(message: Message, settings: Settings) -> bool:
    user = message.from_user
    return user is not None and user.id in settings.telegram_admin_ids


@router.message(Command("create_product"))
async def handle_create_product(message: Message, settings: Settings) -> None:
    """«Создать товар»: admin-only, explains the name + photo format."""
    if is_admin(message, settings):
        await message.answer(CREATE_PRODUCT_INSTRUCTIONS)
    else:
        await answer_with_catalog(message, settings)


@router.message(CommandStart())
@router.message(F.text)
async def handle_any_text(message: Message, settings: Settings) -> None:
    """On start and any ordinary message — offer the Mini App catalog."""
    await answer_with_catalog(message, settings)


@router.message(F.photo)
async def handle_photo(
    message: Message,
    settings: Settings,
    pool: asyncpg.Pool,
    storage_client: Minio,
    bot: Bot,
) -> None:
    """Admin sends name (caption) + photo in one message — create the product."""
    if not is_admin(message, settings):
        await answer_with_catalog(message, settings)
        return
    caption = message.caption
    photos = message.photo
    if caption is None or not caption.strip() or photos is None:
        await message.answer(CREATE_PRODUCT_INSTRUCTIONS)
        return
    name = caption.strip()
    photo = max(photos, key=lambda size: size.width or 0)
    image_key = f"{photo.file_unique_id}.jpg"
    image_buffer = io.BytesIO()
    await bot.download(photo.file_id, destination=image_buffer)
    await s3.upload_image(storage_client, settings.s3_bucket, image_key, image_buffer.getvalue())
    product = await db.insert_product(pool, name, image_key)
    await message.answer(f"Товар «{product.name}» добавлен в каталог.")


@router.errors()
async def handle_error(event: ErrorEvent) -> bool:
    """Never crash the bot on a failed update — log it and keep serving."""
    logger.exception(
        "Failed to process update %d", event.update.update_id, exc_info=event.exception
    )
    return True


async def serve_webhook(
    bot: Bot, dispatcher: Dispatcher, settings: Settings, webhook_url: str
) -> None:
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )
    webapp = web.Application()
    SimpleRequestHandler(
        dispatcher=dispatcher, bot=bot, secret_token=settings.telegram_webhook_secret
    ).register(webapp, path=WEBHOOK_PATH)
    setup_application(webapp, dispatcher, bot=bot)
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.webhook_server_port)
    await site.start()
    logger.info("Webhook server is listening on port %d", settings.webhook_server_port)
    await asyncio.Event().wait()  # serve updates until the process is stopped


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = get_settings()
    pool = await db.create_pool(settings)
    storage_client = s3.create_client(settings)
    session = (
        AiohttpSession(proxy=str(settings.telegram_proxy_url))
        if settings.telegram_proxy_url
        else None
    )
    bot = Bot(token=settings.telegram_bot_token, session=session)
    dispatcher = Dispatcher()
    dispatcher["settings"] = settings
    dispatcher["pool"] = pool
    dispatcher["storage_client"] = storage_client
    dispatcher.include_router(router)
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть каталог"),
            BotCommand(command="create_product", description="Создать товар"),
        ]
    )
    try:
        webhook_url = settings.telegram_webhook_url
        if webhook_url is None:
            await bot.delete_webhook(drop_pending_updates=True)
            await dispatcher.start_polling(bot)
        else:
            await serve_webhook(bot, dispatcher, settings, webhook_url.unicode_string())
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
