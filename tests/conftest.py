"""Общие заготовки для тестов."""
import os

# config.py требует токен при импорте, поэтому задаём тестовый ДО импорта zp_bot.
os.environ["BOT_TOKEN"] = "999999:test-token"

import pytest

from zp_bot import db


@pytest.fixture
def conn():
    """Чистая база в оперативной памяти для каждого теста."""
    connection = db.connect(":memory:")
    yield connection
    connection.close()


@pytest.fixture
def emp_id(conn):
    """Один сотрудник с привязанным Telegram (id 555)."""
    code = db.add_employee(conn, "0001", "Демо Айбек Тестович", "Инженер")
    return db.link_employee(conn, code, 555)["id"]