import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import get_settings
from bot.dependencies import init as init_dependencies
from bot.handlers import hexaco_router, hogan_router, start_router, svs_router
from bot.services import (
    HexacoEngine,
    HoganAtlasInsights,
    HoganEngine,
    HoganInsights,
    SvsEngine,
    StorageGateway,
)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)

    hexaco_engine = HexacoEngine()
    hogan_engine = HoganEngine()
    svs_engine = SvsEngine()
    hogan_insights = HoganInsights()
    hogan_atlas = HoganAtlasInsights()
    storage = StorageGateway(settings.database_path)
    await storage.init()
    init_dependencies(
        hexaco_engine, hogan_engine, svs_engine, storage, hogan_insights, hogan_atlas
    )

    dispatcher.include_router(start_router)
    dispatcher.include_router(hexaco_router)
    dispatcher.include_router(hogan_router)
    dispatcher.include_router(svs_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
