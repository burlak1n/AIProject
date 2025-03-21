from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Рецепты из холодильника", callback_data="fridge"),
                InlineKeyboardButton(text="Определить блюдо", callback_data="food")
            ],
            [
                InlineKeyboardButton(text="Добавить рецепт", callback_data="add_recipe"),
                InlineKeyboardButton(text="Рецепты", callback_data="recipes")
            ],
            [
                InlineKeyboardButton(text="Рассчитай ингредиенты", callback_data="calculate_ingredients"),
                InlineKeyboardButton(text="Найти рецепт", callback_data="find")
            ],
            [
                InlineKeyboardButton(text="Предпочтения", callback_data="preferences"),
                InlineKeyboardButton(text="Показать/Скрыть рецепты", callback_data="privacy")
            ],
            [
                InlineKeyboardButton(text="Спросить у помощника", callback_data="giga"),
                InlineKeyboardButton(text="Проиллюстрировать рецепт", callback_data="image")
            ],
        ],
        resize_keyboard=True,
    )

illustrate_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Проиллюстрировать рецепт", callback_data="image"),
                InlineKeyboardButton(text="Назад в меню", callback_data="menu")
            ],
        ],
        resize_keyboard=True,
    )

menu_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Назад в меню", callback_data="menu")
            ],
        ],
        resize_keyboard=True,
    )