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

SOCIAL_FUND_RATE = 5289
INCOME_TAX_RATE = 0.05
KINDS = ('аванс', "зарплата", "премия", "отпускные")

def calc_withholdings(gross):
    """Считает удержания. Возвращает (соцфонд, подоходный, на руки)"""
    social = round(SOCIAL_FUND_RATE, 2)
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


def employee_by_tab(conn, tab_no):
    """Ищет сотрудника по табельному номеру."""
    return conn.execute(
        "SELECT * FROM employees WHERE tab_no = ?", (tab_no,)
    ).fetchone()

def new_link_code(conn, tab_no):
    """Выдаёт сотруднику новый код и отвязывает старый Telegram."""
    code = secrets.token_hex(3).upper()
    cur = conn.execute(
        "UPDATE employees SET link_code = ?, tg_user_id = NULL, linked_at = NULL WHERE tab_no = ?",
        (code, tab_no),
    )
    conn.commit()
    if cur.rowcount == 0:
        return None
    return code


def pending_notifications(conn):
    """Выплаты, о которых ещё не сообщили привязанным сотрудникам."""
    return conn.execute(
        """SELECT p.*, e.tg_user_id
           FROM payments p
           JOIN employees e ON e.id = p.employee_id
           WHERE p.notified_at IS NULL
             AND e.tg_user_id IS NOT NULL
             AND e.is_active = 1
           ORDER BY p.paid_at, p.id"""
    ).fetchall()


def mark_notified(conn, payment_id):
    """Отмечает, что уведомление о выплате отправлено."""
    conn.execute("UPDATE payments SET notified_at = ? WHERE id = ?", (now(), payment_id))
    conn.commit()

def employee_by_name(conn, full_name):
    """Ищет сотрудника по ФИО (в ведомости 1С нет табельных номеров)."""
    return conn.execute(
        "SELECT * FROM employees WHERE full_name = ?", (full_name,)
    ).fetchone()


def next_tab_no(conn):
    """Следующий свободный табельный: '0001', '0002', ..."""
    row = conn.execute("SELECT MAX(CAST(tab_no AS INTEGER)) AS m FROM employees").fetchone()
    return f"{(row['m'] or 0) + 1:04d}"


def has_salary(conn, employee_id, period):
    """Есть ли уже зарплата сотрудника за этот месяц (защита от двойной загрузки)."""
    row = conn.execute(
        "SELECT 1 FROM payments WHERE employee_id = ? AND period = ? AND kind = 'зарплата'",
        (employee_id, period),
    ).fetchone()
    return row is not None


def add_payment_exact(conn, employee_id, period, kind, gross, social, tax, other, paid_at):
    """Записывает выплату с готовыми удержаниями из 1С, без пересчёта."""
    net = round(gross - social - tax - other, 2)
    cur = conn.execute(
        """INSERT INTO payments
               (employee_id, period, kind, gross, social_fund, income_tax, other_withheld, net, paid_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (employee_id, period, kind, gross, social, tax, other, net, paid_at),
    )
    conn.commit()
    return cur.lastrowid