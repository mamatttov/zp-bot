"""Команды и кнопки бота."""
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from . import db, texts
from .keyboards import BTN_HISTORY, BTN_LAST, BTN_YEAR, main_menu

router = Router()

HELP = (
    "<b>Что я умею</b>\n"
    "/last — последняя выплата\n"
    "/history — история за 6 месяцев\n"
    "/year — итоги за год\n\n"
    "О новых выплатах я сообщаю сам."
)
ASK_CODE = "Отправьте код от бухгалтерии: <code>/link ВАШКОД</code>"


@router.message(CommandStart())
async def cmd_start(message: Message, conn):
    emp = db.employee_by_tg(conn, message.from_user.id)
    if emp is None:
        await message.answer("Здравствуйте! Я присылаю уведомления о зарплате.\n\n" + ASK_CODE)
    else:
        await message.answer(f"С возвращением, {emp['full_name']}!\n\n{HELP}", reply_markup=main_menu)


@router.message(Command("link"))
async def cmd_link(message: Message, command: CommandObject, conn):
    if not command.args:
        await message.answer(ASK_CODE)
        return
    emp = db.link_employee(conn, command.args, message.from_user.id)
    if emp is None:
        await message.answer("Код не найден или уже использован.")
        return
    await message.answer(f"Готово, {emp['full_name']}!\n\n{HELP}", reply_markup=main_menu)


async def get_employee(message: Message, conn):
    """Сотрудник, который пишет боту. Не привязан — просим код."""
    emp = db.employee_by_tg(conn, message.from_user.id)
    if emp is None:
        await message.answer(ASK_CODE)
    return emp



@router.message(Command("last"))
@router.message(F.text == BTN_LAST)
async def cmd_last(message: Message, conn):
    emp = await get_employee(message, conn)
    if emp is None:
        return
    p = db.last_payment(conn, emp["id"])
    if p is None:
        await message.answer("Выплат пока нет.")
    else:
        await message.answer(texts.payment_card(p, "Последняя выплата"))


@router.message(Command("history"))
@router.message(F.text == BTN_HISTORY)
async def cmd_history(message: Message, conn):
    emp = await get_employee(message, conn)
    if emp is None:
        return
    rows = db.monthly_history(conn, emp["id"])
    await message.answer(texts.history(rows))


@router.message(Command("year"))
@router.message(F.text == BTN_YEAR)
async def cmd_year(message: Message, conn):
    emp = await get_employee(message, conn)
    if emp is None:
        return
    year = date.today().year
    await message.answer(texts.year_text(db.year_summary(conn, emp["id"], year), year))


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP, reply_markup=main_menu)


@router.message()
async def fallback(message: Message):
    await message.answer("Не понимаю 🙂 /help — список команд.")