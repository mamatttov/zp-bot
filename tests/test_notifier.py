from aiogram.exceptions import TelegramForbiddenError

from zp_bot import db, notifier


class FakeBot:
    """Вместо отправки в Telegram запоминает сообщения."""

    def __init__(self, error=None):
        self.sent = []
        self.error = error

    async def send_message(self, chat_id, text):
        if self.error:
            raise self.error
        self.sent.append((chat_id, text))


async def test_sends_once(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 0, "2026-11-05")
    bot = FakeBot()
    assert await notifier.send_pending(bot, conn) == 1
    assert await notifier.send_pending(bot, conn) == 0  # повторно не отправляет
    assert bot.sent[0][0] == 555
    assert "Новая выплата" in bot.sent[0][1]


async def test_unlinked_employee_gets_nothing(conn):
    db.add_employee(conn, "0002", "Демо Мария Шаблонова", "Юрист")
    db.add_payment(conn, 1, "2026-10", "зарплата", 55000, 5500, 4950, 0, "2026-11-05")
    assert await notifier.send_pending(FakeBot(), conn) == 0
    assert len(db.pending_notifications(conn)) == 0  # но выплата ждёт привязки
    assert conn.execute("SELECT notified_at FROM payments").fetchone()[0] is None


async def test_network_error_retries_later(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 0, "2026-11-05")
    assert await notifier.send_pending(FakeBot(error=RuntimeError("сеть")), conn) == 0
    assert len(db.pending_notifications(conn)) == 1  # осталась в очереди
    assert await notifier.send_pending(FakeBot(), conn) == 1


async def test_blocked_user_not_retried(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 0, "2026-11-05")
    blocked = TelegramForbiddenError(method=None, message="bot was blocked by the user")
    await notifier.send_pending(FakeBot(error=blocked), conn)
    assert len(db.pending_notifications(conn)) == 0  # не пытаемся бесконечно