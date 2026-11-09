"""Запуск бота: python -m zp_bot"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from . import config, db
from .handlers import router
from .notifier import notifier_loop

COMMANDS = [
    BotCommand(command="start", description="Начать"),
    BotCommand(command="last", description="Последняя выплата"),
    BotCommand(command="history", description="История за 6 месяцев"),
    BotCommand(command="year", description="Итоги года"),
    BotCommand(command="help", description="Помощь"),
]


async def main():
    logging.basicConfig(level=logging.INFO)
    conn = db.connect(config.DB_PATH)
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["conn"] = conn
    dp.include_router(router)

    await bot.set_my_commands(COMMANDS)
    task = asyncio.create_task(notifier_loop(bot, conn, config.NOTIFY_INTERVAL))
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
        conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")