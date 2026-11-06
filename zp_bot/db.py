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


# Выплаты

SOCIAL_FUND_RATE = 0.10
INCOME_TAX_RATE = 0.10
KINDS = ('аванс', "зарплата", "премия", "отпускные")

def calc_withholdings(gross):
    """Считает удержания. Возвращает (соцфонд, подоходный, на руки)"""
    social = round(gross * SOCIAL_FUND_RATE, 2)
    tax = round((gross - social) * INCOME_TAX_RATE, 2)
    net = round(gross - social - tax, 2)
    return social, tax, net


def add_payment(conn, employee_id, period, kind, gross, paid_at, notified = False):
    """Записывает выплату и возвращает ее id"""
    if kind not in KINDS:
        raise ValueError(f"Неизвестный вид оплаты: {kind}")
    social, tax, net = calc_withholdings(gross)
    notified_at = now() if notified else None
    cur = conn.execute(
        """INSERT INTO payments
                (employee_id, period, kind, gross, social_fund, income_tax, net, paid_at, notified_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (employee_id, period, kind, gross, social, tax, net, paid_at, notified_at),
    )
    conn.commit()
    return cur.lastrowid


def last_payment(conn, employee_id):
    """Самая свежая выплата сотрудника или None"""
    return conn.execute(
        """SELECT * FROM payments 
            WHERE employee_id = ?
            ORDER BY paid_at DESC, id DESC
            LIMIT 1""",
        (employee_id,),
    ).fetchone()

def monthly_history(conn, employee_id, limit = 6):
    """Последние месяцы, новые сверху, с разницей к прошлому месяцу."""
    return conn.execute(
        """SELECT period, gross, withheld, net, payments_cnt,
                ROUND(net - LAG(net) OVER (ORDER BY period), 2) AS diff
                FROM v_monthly
        WHERE employee_id = ?
        ORDER BY period DESC
        LIMIT ?""",
        (employee_id, limit),
    ).fetchall()


def year_summary(conn, employee_id, year):
    """Итоги за год: суммы, среднее, лучший месяц. Нет выплат - None"""
    row = conn.execute(
        """WITH m AS( SELECT * FROM v_monthly
               WHERE employee_id = ? AND substr(period, 1, 4) = ?
           )
       SELECT ROUND(SUM(gross), 2)    AS gross,
                  ROUND(SUM(withheld), 2) AS withheld,
                  ROUND(SUM(net), 2)      AS net,
                  COUNT(*)                AS months,
                  ROUND(AVG(net), 2)      AS avg_net,
                  (SELECT period FROM m ORDER BY net DESC LIMIT 1) AS best_period,
                  MAX(net)                AS best_net
           FROM m""",
        (employee_id, str(year)),
    ).fetchone()
    if row['months'] == 0:
        return None
    return row
