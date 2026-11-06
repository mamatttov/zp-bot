# Работа с базой SQLite. Весь SQL проекта живет в этом файле

import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'schema.sql'

def connect(path):
    """Открывает базу и создаёт таблицы, если их ещё нет"""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
    return conn


def now():
    return datetime.now().isoformat(timespec='seconds')


def add_employee(conn, tab_no, full_name, position):
    """Добавляет сотрудника и возвращает код привязки Телеграм"""
    code = secrets.token_hex(3).upper()
    conn.execute(
        "INSERT INTO employees (tab_no, full_name, position, link_code) VALUES (?, ?, ?, ?)",
        (tab_no, full_name, position, code)
    )
    conn.commit()
    return code


def employee_by_tg(conn, tg_user_id):
    """Ищет сотрудника по Telegram id. Нет такого - вернет None."""
    return conn.execute(
        'SELECT * FROM employees WHERE tg_user_id = ? AND is_active = 1',  (tg_user_id,)
    ).fetchone()


def link_employee(conn, code, tg_user_id):
    """Привязывает Телеграм к сотруднику по однаразовому коду."""
    code = code.strip().upper()
    row = conn.execute(
        'SELECT * FROM employees WHERE link_code = ? AND is_active = 1',
        (code,)
    ).fetchone()
    if row is None:
        return None
    conn.execute(
        'UPDATE employees SET tg_user_id = ?, link_code = NULL, linked_at = ? WHERE id = ?',
        (tg_user_id, now(), row['id'])
    )
    conn.commit()
    return employee_by_tg(conn, tg_user_id)

