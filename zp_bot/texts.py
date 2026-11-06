"""Тексты сообщений бота"""

MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]


def money(x):
    """40500.5 -> '40 500,50 сом"""
    s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} сом"


def period_name(period):
    """'2026-10' -> 'октябрь 2026' """
    year, month = period.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def date_ru(iso):
    """'2026-10-05' - '05.10.2026' """
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def payment_card(p, title = "Выплата"):
    """Карточка одной выплаты"""
    return (
        f"<b>{title}: {p['kind']}</b> за {period_name(p['period'])}\n"
        f"Дата: {date_ru(p['paid_at'])}\n\n"
        f"Начислено: {money(p['gross'])}\n"
        f"Соцфонд: −{money(p['social_fund'])}\n"
        f"Подоходный налог: −{money(p['income_tax'])}\n"
        f"<b>На руки: {money(p['net'])}</b>"
    )


def history(rows):
    """История по месяцам со стрелками ▲▼."""
    if not rows:
        return "Выплат пока нет."
    lines = ["<b>История по месяцам</b> (на руки)\n"]
    for r in rows:
        line = f"{period_name(r['period'])}: <b>{money(r['net'])}</b>"
        if r["diff"]:
            arrow = "▲" if r["diff"] > 0 else "▼"
            line += f"  {arrow} {money(abs(r['diff']))}"
        lines.append(line)
    return "\n".join(lines)


def year_text(s, year):
    """Итоги за год."""
    if s is None:
        return f"За {year} год выплат нет."
    return (
        f"<b>Итоги за {year} год</b>\n\n"
        f"Месяцев с выплатами: {s['months']}\n"
        f"Начислено: {money(s['gross'])}\n"
        f"Удержано: {money(s['withheld'])}\n"
        f"<b>Получено на руки: {money(s['net'])}</b>\n"
        f"В среднем за месяц: {money(s['avg_net'])}\n"
        f"Лучший месяц: {period_name(s['best_period'])} ({money(s['best_net'])})"
    )