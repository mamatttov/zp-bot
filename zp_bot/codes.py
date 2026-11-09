"""Коды привязки сотрудников.

Запуск:
    python -m zp_bot.codes            список сотрудников и их коды
    python -m zp_bot.codes 0002       выдать новый код сотруднику 0002
"""
import sys

from . import config, db


def show_all(conn):
    rows = conn.execute(
        "SELECT tab_no, full_name, link_code, tg_user_id FROM employees ORDER BY tab_no"
    ).fetchall()
    for r in rows:
        if r["link_code"]:
            status = f"код: /link {r['link_code']}"
        else:
            status = "уже привязан"
        print(f"{r['tab_no']}  {r['full_name']:<28} {status}")


def main():
    conn = db.connect(config.DB_PATH)
    if len(sys.argv) == 1:
        show_all(conn)
        return
    tab_no = sys.argv[1]
    code = db.new_link_code(conn, tab_no)
    if code is None:
        print(f"Нет сотрудника с табельным {tab_no}")
    else:
        print(f"Новый код для {tab_no}: /link {code}")


if __name__ == "__main__":
    main()