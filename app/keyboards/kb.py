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
            ]
        ],
        resize_keyboard=True,
    )