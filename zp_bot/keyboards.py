"""Кнопки меню."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_LAST = "💰 Последняя выплата"
BTN_HISTORY = "📊 История"
BTN_YEAR = "📅 Итоги года"

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_LAST)],
        [KeyboardButton(text=BTN_HISTORY), KeyboardButton(text=BTN_YEAR)],
    ],
    resize_keyboard=True,
)