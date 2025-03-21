from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Рецепт из холодильника 🍳", callback_data="fridge"),
                InlineKeyboardButton(text="Определить блюдо 🍔", callback_data="food")
            ],
            [
                InlineKeyboardButton(text="Добавить рецепт 🗒️", callback_data="add_recipe"),
                InlineKeyboardButton(text="Мои рецепты 📕", callback_data="recipes"),
            ],
            [
                InlineKeyboardButton(text="Случайный рецепт 👁️", callback_data="random_me"),
                InlineKeyboardButton(text="Рассчитай ингредиенты 🧮", callback_data="calculate_ingredients"),
            ],
            [
                InlineKeyboardButton(text="Предпочтения 💕", callback_data="preferences"),
            ],
            [
                InlineKeyboardButton(text="Искать рецепты 🙋‍♂️", callback_data="giga")
            ],
        ],
        resize_keyboard=True,
    )

illustrate_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Проиллюстрировать рецепт 🖼️", callback_data="image"),
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
            ],
        ],
        resize_keyboard=True,
    )

menu_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
            ],
        ],
        resize_keyboard=True,
    )

random = InlineKeyboardMarkup(
        inline_keyboard=[
            [   
                InlineKeyboardButton(text="Добавить рецепт 🗒️", callback_data="add_recipe"),
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")
            ],
        ],
        resize_keyboard=True,
    )