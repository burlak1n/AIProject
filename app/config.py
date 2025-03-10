import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DB_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/db.sqlite3"
    TOKEN: str
    GigaChatKey: str
    kandinsky_api_key: str
    kandinsky_secret_key: str

    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")

# Получаем параметры для загрузки переменных среды
settings = Settings()
DB_URL = settings.DB_URL
TOKEN = settings.TOKEN
GigaChatKey = settings.GigaChatKey
kandinsky_api_key=settings.kandinsky_api_key
kandinsky_secret_key=settings.kandinsky_secret_key