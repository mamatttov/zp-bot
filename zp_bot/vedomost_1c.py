"""Загрузка «Расчетной ведомости» из 1С (Excel .xlsx).

Запуск:
    python -m zp_bot.vedomost_1c путь\\к\\ведомости.xlsx --date 2026-10-05

Удержания берём из ведомости как есть, ничего не пересчитываем.
"""
import argparse
import re
from datetime import date

from openpyxl import load_workbook

from . import config, db

MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


def simple(text):
    """'Всего\\nудержано ' -> 'всего удержано'"""
    return " ".join(str(text or "").lower().split())


def to_number(value):
    """Число из ячейки: 1234.5, '1 234,50' или пусто -> float."""
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace("\xa0", "").replace(" ", "").replace(",", "."))


def find_header(sheet):
    """Строка шапки: в первом столбце «Подразделение», под ней «Сотрудник»."""
    for r in range(1, 30):
        if simple(sheet.cell(r, 1).value) == "подразделение" and simple(sheet.cell(r + 1, 1).value) == "сотрудник":
            return r
    raise SystemExit("Не нашёл шапку ведомости (строки «Подразделение» и «Сотрудник»).")


def find_period(sheet):
    """'Расчетная ведомость за Сентябрь 2026 г.' -> '2026-09'"""
    for r in range(1, 6):
        found = re.search(r"за\s+(\w+)\s+(\d{4})", str(sheet.cell(r, 1).value or ""), re.IGNORECASE)
        if found and found.group(1).lower() in MONTHS:
            month = MONTHS.index(found.group(1).lower()) + 1
            return f"{found.group(2)}-{month:02d}"
    raise SystemExit("Не нашёл период в заголовке («Расчетная ведомость за ... 2026 г.»).")


def find_columns(sheet, header_row):
    """Номера нужных столбцов по названиям в шапке."""
    cols = {}
    for c in range(1, sheet.max_column + 1):
        name = simple(sheet.cell(header_row, c).value)
        if name and name not in cols:
            cols[name] = c
    if "начислено" not in cols:
        raise SystemExit("В шапке нет столбца «Начислено».")
    return {
        "gross": cols["начислено"],
        "pfr": cols.get("пфр"),
        "gnpfr": cols.get("гнпфр"),
        "pn": cols.get("пн"),
        "total": cols.get("всего удержано") or cols.get("удержано"),
    }


def is_employee_row(sheet, r):
    """В 1С сотрудники вложены в подразделение (уровень группировки 1),
    а подразделения выделены жирным."""
    if sheet.row_dimensions[r].outline_level >= 1:
        return True
    return not sheet.cell(r, 1).font.b


def read_vedomost(path):
    """Возвращает (период, [словарь на каждого сотрудника])."""
    sheet = load_workbook(path, data_only=True).worksheets[0]
    period = find_period(sheet)
    header_row = find_header(sheet)
    cols = find_columns(sheet, header_row)

    def amount(r, key):
        return to_number(sheet.cell(r, cols[key]).value) if cols[key] else 0.0

    people = []
    for r in range(header_row + 2, sheet.max_row + 1):
        name = str(sheet.cell(r, 1).value or "").strip()
        if not name:
            continue
        if name.lower().startswith("итого"):
            break
        if not is_employee_row(sheet, r):
            continue
        social = amount(r, "pfr") + amount(r, "gnpfr")
        tax = amount(r, "pn")
        total = amount(r, "total")
        people.append({
            "row": r,
            "full_name": name,
            "gross": amount(r, "gross"),
            "social": round(social, 2),
            "tax": round(tax, 2),
            "other": round(max(total - social - tax, 0), 2),
        })
    return period, people


def import_vedomost(conn, path, paid_at):
    period, people = read_vedomost(path)
    print(f"Ведомость за {period}, строк сотрудников: {len(people)}")
    added = 0
    for p in people:
        if p["gross"] == 0:
            print(f"- строка {p['row']}: {p['full_name']} — начислений нет, пропускаю")
            continue
        emp = db.employee_by_name(conn, p["full_name"])
        if emp is None:
            code = db.add_employee(conn, db.next_tab_no(conn), p["full_name"], "")
            emp = db.employee_by_name(conn, p["full_name"])
            print(f"+ новый сотрудник {emp['tab_no']} {p['full_name']}: код {code}")
        if db.has_salary(conn, emp["id"], period):
            print(f"= {p['full_name']}: зарплата за {period} уже загружена")
            continue
        db.add_payment_exact(conn, emp["id"], period, "зарплата",
                             p["gross"], p["social"], p["tax"], p["other"], paid_at)
        added += 1
    print(f"Добавлено выплат: {added}")


def main():
    parser = argparse.ArgumentParser(description="Загрузка расчётной ведомости из 1С")
    parser.add_argument("path", help="файл .xlsx из 1С")
    parser.add_argument("--date", default=date.today().isoformat(), help="дата выплаты ГГГГ-ММ-ДД")
    parser.add_argument("--check", action="store_true", help="только показать, не записывать")
    args = parser.parse_args()
    if args.check:
        preview(args.path)
        return
    conn = db.connect(config.DB_PATH)
    import_vedomost(conn, args.path, args.date)


def preview(path):
    """Показывает, что будет загружено, ничего не записывая в базу."""
    period, people = read_vedomost(path)
    print(f"Ведомость за {period}. В базу НИЧЕГО не записано.\n")
    print(f"{'ФИО':<32}{'Начислено':>12}{'Соцфонд':>11}{'ПН':>10}{'Прочие':>9}{'На руки':>12}")
    total = 0
    for p in people:
        net = round(p["gross"] - p["social"] - p["tax"] - p["other"], 2)
        total += net
        print(f"{p['full_name'][:31]:<32}{p['gross']:>12,.2f}{p['social']:>11,.2f}"
              f"{p['tax']:>10,.2f}{p['other']:>9,.2f}{net:>12,.2f}")
    print(f"\nИтого на руки: {total:,.2f}")


if __name__ == "__main__":
    main()
