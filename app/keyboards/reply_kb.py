from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

reply_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Рецепты из холодильника"),
            KeyboardButton(text="Определить блюдо")
        ],
        [
            KeyboardButton(text="Добавить рецепт"),
            KeyboardButton(text="Рецепты")
        ],
        [
            KeyboardButton(text="Случайный рецепт"),
            KeyboardButton(text="Найти рецепт")
        ],
        [
            KeyboardButton(text="Предпочтения"),
            KeyboardButton(text="Показать/Скрыть рецепты")
        ],
        [
            KeyboardButton(text="Спросить у помощника"),
            KeyboardButton(text="Сгенерировать фото")
        ],
    ],
    resize_keyboard=True,  # Автоматически подстраивает размер клавиатуры
)