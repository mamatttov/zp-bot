import sqlite3

import pytest

from zp_bot import db


def test_link_code_works_once(conn):
    code = db.add_employee(conn, "0001", "Демо Айбек Тестович", "Инженер")
    assert db.link_employee(conn, code, 555)["tab_no"] == "0001"
    assert db.link_employee(conn, code, 777) is None  # код уже использован


def test_wrong_code_returns_none(conn):
    db.add_employee(conn, "0001", "Демо Айбек Тестович", "Инженер")
    assert db.link_employee(conn, "ZZZZZZ", 555) is None


def test_duplicate_tab_no_rejected(conn):
    db.add_employee(conn, "0001", "Демо Айбек Тестович", "Инженер")
    with pytest.raises(sqlite3.IntegrityError):
        db.add_employee(conn, "0001", "Демо Мария Шаблонова", "Юрист")


def test_net_is_gross_minus_withholdings(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 600, "2026-11-05")
    p = db.last_payment(conn, emp_id)
    assert p["net"] == 48000
    assert p["other_withheld"] == 600


def test_unknown_kind_rejected(conn, emp_id):
    with pytest.raises(ValueError):
        db.add_payment(conn, emp_id, "2026-10", "подарок", 500, 0, 0, 0, "2026-11-05")


def test_bad_period_rejected_by_database(conn, emp_id):
    with pytest.raises(sqlite3.IntegrityError):
        db.add_payment(conn, emp_id, "октябрь", "зарплата", 500, 0, 0, 0, "2026-11-05")


def test_history_shows_difference_to_previous_month(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-09", "зарплата", 50000, 5000, 4500, 0, "2026-10-05")
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 0, "2026-11-05")
    rows = db.monthly_history(conn, emp_id)
    assert [r["period"] for r in rows] == ["2026-10", "2026-09"]
    assert rows[0]["diff"] == 8100   # 48 600 − 40 500
    assert rows[1]["diff"] is None   # у первого месяца сравнивать не с чем


def test_year_summary(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-09", "зарплата", 50000, 5000, 4500, 0, "2026-10-05")
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 0, "2026-11-05")
    s = db.year_summary(conn, emp_id, 2026)
    assert s["months"] == 2
    assert s["net"] == 89100
    assert s["best_period"] == "2026-10"
    assert db.year_summary(conn, emp_id, 2020) is None


def test_new_link_code_unlinks_telegram(conn, emp_id):
    code = db.new_link_code(conn, "0001")
    assert db.employee_by_tg(conn, 555) is None
    assert db.link_employee(conn, code, 777)["tab_no"] == "0001"
    assert db.new_link_code(conn, "9999") is None