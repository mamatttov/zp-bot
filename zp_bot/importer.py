"""Загрузка сотрудников и выплат из CSV.

Запуск:
    python -m zp_bot.importer sotrudniki sample/sotrudniki.csv
    python -m zp_bot.importer vyplaty sample/vyplaty.csv
"""
import argparse
import csv
import sqlite3

from . import config, db


def read_csv(path):
    """Читает CSV с разделителем ';' и возвращает список словарей."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def import_employees(conn, path):
    """Добавляет сотрудников. Уже существующих пропускает."""
    for row in read_csv(path):
        tab_no = row["tab_no"].strip()
        try:
            code = db.add_employee(conn, tab_no, row["full_name"].strip(), row["position"].strip())
            print(f"+ {tab_no} {row['full_name']}: код {code}")
        except sqlite3.IntegrityError:
            print(f"= {tab_no} уже есть, пропускаю")


def import_payments(conn, path):
    """Добавляет выплаты. Строки с ошибками пропускает и показывает."""
    added = 0
    for line_no, row in enumerate(read_csv(path), start=2):
        emp = db.employee_by_tab(conn, row["tab_no"].strip())
        if emp is None:
            print(f"! строка {line_no}: нет сотрудника {row['tab_no']}")
            continue
        try:
            num = lambda key: float(row[key].replace(",", ".").replace(" ", "") or 0)
            db.add_payment(conn, emp["id"], row["period"].strip(), row["kind"].strip(),
                           num("gross"), num("social_fund"), num("income_tax"),
                           num("other_withheld"), row["paid_at"].strip())
            added += 1
        except (ValueError, sqlite3.IntegrityError) as e:
            print(f"! строка {line_no}: {e}")
    print(f"Добавлено выплат: {added}")


def main():
    parser = argparse.ArgumentParser(description="Загрузка данных из CSV")
    parser.add_argument("what", choices=["sotrudniki", "vyplaty"])
    parser.add_argument("path")
    args = parser.parse_args()

    conn = db.connect(config.DB_PATH)
    if args.what == "sotrudniki":
        import_employees(conn, args.path)
    else:
        import_payments(conn, args.path)


if __name__ == "__main__":
    main()