from zp_bot import db, texts

print(texts.money(40500.5), "|", texts.period_name("2026-10"), "|", texts.date_ru("2026-11-05"))

c = db.connect(":memory:")
db.add_employee(c, "0001", "Демо Айбек", "Бухгалтер")
db.add_payment(c, 1, "2026-09", "зарплата", 50000, "2026-10-05")
db.add_payment(c, 1, "2026-10", "зарплата", 45000, "2026-11-05")

print(texts.payment_card(db.last_payment(c, 1), "Последняя выплата"))
print()
print(texts.history(db.monthly_history(c, 1)))
print()
print(texts.year_text(db.year_summary(c, 1, 2026), 2026))
print(texts.year_text(None, 2024))