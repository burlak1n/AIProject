import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DB_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/db.sqlite3"
    TOKEN: str
    GigaChatKey: str = ""
    kandinsky_api_key: str = ""
    kandinsky_secret_key: str = ""
    OPENAI_API_KEY: str = ""
    PROXY: str = ""
    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")

# Получаем параметры для загрузки переменных среды
settings = Settings()
DB_URL = settings.DB_URL
TOKEN = settings.TOKEN
GigaChatKey = settings.GigaChatKey
kandinsky_api_key=settings.kandinsky_api_key
kandinsky_secret_key=settings.kandinsky_secret_key

# ---------- Настройки ----------
PROXY = settings.PROXY
OPENAI_API_KEY = settings.OPENAI_API_KEY

# ---------- Ограничение по длине сообщения ----------
MAX_MESSAGE_LENGTH = 4096

# Базовые промпты для каждой задачи
FRIDGE_IMAGE_PROMPT = "После анализа изображения составь список блюд, которые можно приготовить. Для одного из вариантов предоставь полный рецепт на одну порцию, включающий граммовку ингредиентов и общую калорийность, а также подробную пошаговую инструкцию по приготовлению."
FOOD_IMAGE_PROMPT = "После анализа изображения опиши, что это за продукт. Составь список ингредиентов, необходимых для его приготовления, укажи граммовку для одной порции, а также калорийность как всего блюда, так и отдельных компонентов. Затем предложи рецепт, включающий временные рамки и пошаговое описание процесса приготовления."
PREFERENCES_TEXT_PROMPT = "На основе полученного описания предпочтений составь список из трёх различных блюд, которые можно приготовить. Для каждого блюда предоставь подробную инструкцию по приготовлению, а также укажи граммовку ингредиентов и калорийность."
