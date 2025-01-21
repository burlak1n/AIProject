from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
import asyncio
import aiofiles
import json
import csv

from loguru import logger
from app.api.dao import UsersDAO
from app.api.models import User

from app.create_bot import bot, dp, scheduler
from app.keyboards.kb import main_kb
# import app.api.utils as ut
from app.api.router import r_user as router_recipes
from app.api.router import scheduled_task
# from app.schedule.schedule import start_scheduler
from app.api.schemas import GetUserDB, AddUserDB
from app.dao.session_maker import session_manager

from sqlalchemy.ext.asyncio import AsyncSession

# GigaChat api автоматическая транскрибация. Можно ли отправить голос?
# Улучшить связь между пользователем и рецептом (Блог и аавтор)
# Все рецепты, которые вы сохраните, могут быть использованы другими пользователями, как и вы сможете использовать их рецепты
# При добавлении рецепта: embeddings меняется
# Доступ к роутеру по админке

hello_message = "Привет! Я твой помощник в мире кулинарии.\n"
# Инициализация бота
router_main = Router()

class Image(StatesGroup):
    image = State()

class RegisterUser(StatesGroup):
    started = State()

# @router_main.message(Command("image"))
# async def name_menu(message:Message, state: FSMContext):
#     await state.set_state(Image.image)
#     await message.reply("Введите сообщение, по которому Kandinsky сгенерирует фотографию")

@router_main.message(CommandStart())
@session_manager.connection()
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    m = message.from_user
    user: User = await UsersDAO.find_one_or_none(session, GetUserDB(telegram_id=m.id))
    if not user:
        await state.set_state(RegisterUser.started)
        await message.answer("Для начала введите свою почту")
        return
    await message.answer(f"{hello_message}", reply_markup=main_kb)

@router_main.message(RegisterUser.started)
@session_manager.connection()
async def register_user(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    m = message.from_user
    email = message.text
    await UsersDAO.add(session, AddUserDB(telegram_id=m.id, username=m.username, fullname=m.full_name, email=email))
    await message.answer(f"{hello_message}", reply_markup=main_kb)

async def on_startup():
    logger.info("Starting bot...")
    scheduler.add_job(scheduled_task, "interval", days=1)  # Schedule every 10 seconds
    scheduler.start()

async def on_shutdown():
    logger.info("Shutting down...")
    scheduler.shutdown()
    await dp.storage.close()
    await bot.close()

async def main():
    dp.include_routers(
        router_main,
        router_recipes
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)

if __name__ == "__main__":
    # scheduler = multiprocessing.Process(target=start_scheduler())
    # scheduler.start()
    asyncio.run(main())