"""Запуск бота: python -m zp_bot"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import config, db
from .handlers import router


async def main():
    logging.basicConfig(level=logging.INFO)
    conn = db.connect(config.DB_PATH)
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["conn"] = conn
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())