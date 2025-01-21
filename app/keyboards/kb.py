from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/help"),
                KeyboardButton(text="/add_recipe"),
                KeyboardButton(text="/recipes"),
            ],
            [
                KeyboardButton(text="/random_recipe"),
                KeyboardButton(text="/image"),
                KeyboardButton(text="/find"),
            ],
            [
                KeyboardButton(text="/privacy"),
                KeyboardButton(text="/giga"),
            ],
        ],
        resize_keyboard=True,
    )