from zp_bot import db, texts


def test_money():
    assert texts.money(40500.5) == "40 500,50 сом"


def test_period_and_date():
    assert texts.period_name("2026-10") == "октябрь 2026"
    assert texts.date_ru("2026-11-05") == "05.11.2026"


def test_payment_card_hides_empty_other_withholdings(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 0, "2026-11-05")
    card = texts.payment_card(db.last_payment(conn, emp_id))
    assert "На руки: 48 600,00 сом" in card
    assert "Прочие удержания" not in card


def test_payment_card_shows_other_withholdings(conn, emp_id):
    db.add_payment(conn, emp_id, "2026-10", "зарплата", 60000, 6000, 5400, 600, "2026-11-05")
    assert "Прочие удержания: −600,00 сом" in texts.payment_card(db.last_payment(conn, emp_id))


def test_empty_history_and_year():
    assert texts.history([]) == "Выплат пока нет."
    assert texts.year_text(None, 2024) == "За 2024 год выплат нет."