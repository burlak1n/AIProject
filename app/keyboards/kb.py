from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Рецепты из холодильника", callback_data="fridge"),
                InlineKeyboardButton(text="Определить блюдо", callback_data="food"),
                InlineKeyboardButton(text="Индивидуальные предпочтения", callback_data="preferences"),
            ],
            [
                InlineKeyboardButton(text="Помощь", callback_data="help"),
                InlineKeyboardButton(text="Добавить рецепт", callback_data="add_recipe"),
                InlineKeyboardButton(text="Рецепты", callback_data="recipes"),
            ],
            [
                InlineKeyboardButton(text="Случайный рецепт", callback_data="random_recipe"),
                InlineKeyboardButton(text="Сгенерировать фото", callback_data="image"),
                InlineKeyboardButton(text="Найти рецепт", callback_data="find"),
            ],
            [
                InlineKeyboardButton(text="Конфиденциальность", callback_data="privacy"),
                InlineKeyboardButton(text="Giga", callback_data="giga"),
            ],
        ],
        resize_keyboard=True,
    )