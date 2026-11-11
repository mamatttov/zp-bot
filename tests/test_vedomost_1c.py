import pytest
from openpyxl import Workbook
from openpyxl.styles import Font

from zp_bot import db, vedomost_1c


@pytest.fixture
def vedomost(tmp_path):
    """Маленькая ведомость в формате 1С: подразделение жирным, сотрудники под ним."""
    wb = Workbook()
    ws = wb.active
    rows = [
        ['ОсОО "Демо Компания"'],
        ["Расчетная ведомость за Октябрь 2026 г."],
        ["Подразделение", "Начислено", "ПФР", "ГНПФР", "ПН", "Проф.взнос", "Всего удержано"],
        ["Сотрудник"],
        ["Основное подразделение", 115000],
        ["Демо Нурлан Образцович", 60000, 4800, 1200, 5400, 600, 12000],
        ["Демо Мария Шаблонова", 55000, 4400, 1100, 4950, None, 10450],
        ["Демо Айбек Тестович", None],
        ["Итого", 115000],
    ]
    for row in rows:
        ws.append(row)
    ws["A5"].font = Font(bold=True)
    for r in (6, 7, 8):
        ws.row_dimensions[r].outline_level = 1
    path = tmp_path / "vedomost.xlsx"
    wb.save(path)
    return path


def test_read_vedomost(vedomost):
    period, people = vedomost_1c.read_vedomost(vedomost)
    assert period == "2026-10"
    assert [p["full_name"] for p in people] == [
        "Демо Нурлан Образцович", "Демо Мария Шаблонова", "Демо Айбек Тестович"]
    nurlan = people[0]
    assert (nurlan["gross"], nurlan["social"], nurlan["tax"], nurlan["other"]) == (60000, 6000, 5400, 600)


def test_import_is_idempotent(conn, vedomost):
    vedomost_1c.import_vedomost(conn, vedomost, "2026-11-05")
    vedomost_1c.import_vedomost(conn, vedomost, "2026-11-05")  # повторная загрузка
    assert conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 2
    # сотрудник без начислений не создаётся
    assert db.employee_by_name(conn, "Демо Айбек Тестович") is None
    nurlan = db.employee_by_name(conn, "Демо Нурлан Образцович")
    assert db.last_payment(conn, nurlan["id"])["net"] == 48000


def test_preview_writes_nothing(conn, vedomost, capsys):
    vedomost_1c.preview(vedomost)
    assert "Итого на руки: 92,550.00" in capsys.readouterr().out
    assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0