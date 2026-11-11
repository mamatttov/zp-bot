from zp_bot import db, importer


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_import_employees_skips_duplicates(conn, tmp_path):
    f = write(tmp_path / "s.csv", "tab_no;full_name;position\n0001;Демо Айбек Тестович;Инженер\n")
    importer.import_employees(conn, f)
    importer.import_employees(conn, f)  # второй раз не падает и не дублирует
    assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 1


def test_import_payments_skips_bad_rows(conn, tmp_path, capsys):
    db.add_employee(conn, "0001", "Демо Айбек Тестович", "Инженер")
    f = write(tmp_path / "v.csv",
              "tab_no;period;kind;gross;social_fund;income_tax;other_withheld;paid_at\n"
              "0001;2026-10;зарплата;54 000,50;5400;4860;;2026-11-05\n"
              "0009;2026-10;аванс;1000;0;0;0;2026-10-20\n"       # нет такого сотрудника
              "0001;2026-10;подарок;500;0;0;0;2026-11-05\n")     # неизвестный вид выплаты
    importer.import_payments(conn, f)
    rows = conn.execute("SELECT gross, net FROM payments").fetchall()
    assert len(rows) == 1
    assert rows[0]["gross"] == 54000.5
    assert rows[0]["net"] == 43740.5
    out = capsys.readouterr().out
    assert "строка 3" in out and "строка 4" in out