"""Временный скрипт: один демо-сотрудник с выплатами в data/zp.db."""
from zp_bot import db

conn = db.connect("data/zp.db")
code = db.add_employee(conn, "0001", "Демо Айбек Тестович", "Бухгалтер")
emp_id = conn.execute("SELECT id FROM employees WHERE tab_no = '0001'").fetchone()["id"]

for month in range(1, 11):
    period = f"2026-{month:02d}"
    db.add_payment(conn, emp_id, period, "аванс", 20000, f"{period}-20", notified=True)
    db.add_payment(conn, emp_id, period, "зарплата", 30000 + month * 500, f"{period}-28", notified=True)

print("Код привязки:", code)