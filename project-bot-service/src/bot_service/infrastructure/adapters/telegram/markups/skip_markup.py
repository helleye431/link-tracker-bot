from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

skip_keyboard_markup = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Пропустить")]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
