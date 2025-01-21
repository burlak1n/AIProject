import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DB_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/db.sqlite3"

    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")
    TOKEN: str = model_config.get("TOKEN")
    GigaChatKey: str = model_config.get("GigaChatKey")
    kandinsky_api_key: str = model_config.get("kandinsky_api_key")
    kandinsky_secret_key: str = model_config.get("kandinsky_secret_key")

# Получаем параметры для загрузки переменных среды
settings = Settings()
DB_URL = settings.DB_URL
TOKEN = settings.TOKEN
GigaChatKey = settings.GigaChatKey
kandinsky_api_key=settings.kandinsky_api_key
kandinsky_secret_key=settings.kandinsky_secret_key