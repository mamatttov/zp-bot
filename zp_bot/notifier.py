"""Фоновая рассылка уведомлений о новых выплатах."""
import asyncio
import logging

from aiogram.exceptions import TelegramForbiddenError

from . import db, texts

log = logging.getLogger(__name__)


async def send_pending(bot, conn):
    """Один проход: отправить все неотправленные уведомления."""
    sent = 0
    for p in db.pending_notifications(conn):
        try:
            await bot.send_message(p["tg_user_id"], "💰 " + texts.payment_card(p, "Новая выплата"))
            sent += 1
        except TelegramForbiddenError:
            log.warning("Пользователь %s заблокировал бота", p["tg_user_id"])
        except Exception:
            log.exception("Не удалось отправить выплату %s", p["id"])
            continue
        db.mark_notified(conn, p["id"])
        await asyncio.sleep(0.05)
    return sent


async def notifier_loop(bot, conn, interval):
    """Каждые interval секунд проверяет базу на новые выплаты."""
    while True:
        try:
            n = await send_pending(bot, conn)
            if n:
                log.info("Отправлено уведомлений: %s", n)
        except Exception:
            log.exception("Ошибка в цикле уведомлений")
        await asyncio.sleep(interval)