import logging
import sys
from app.config import TOKEN
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import PROXY
from aiogram.client.session.aiohttp import AiohttpSession


# Базовое логирование
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

session = AiohttpSession(
    proxy=PROXY
)

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
scheduler = AsyncIOScheduler()
