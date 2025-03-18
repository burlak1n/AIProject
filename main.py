from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.filters import CommandStart
import asyncio

from loguru import logger
from app.api.dao import UsersDAO
from app.api.models import User

from app.create_bot import bot, dp, scheduler
from app.keyboards.kb import main_kb
from app.api.router import r_user as router_recipes
from app.api.router import scheduled_task
from app.api.schemas import GetUserDB, AddUserDB
from app.dao.session_maker import session_manager
from app.api.router_fridge import router as router_fridge
from sqlalchemy.ext.asyncio import AsyncSession

hello_message = "Я твой помощник в мире кулинарии.\n"
router_main = Router()

class RegisterUser(StatesGroup):
    started = State()
    contra = State()

@dp.message(CommandStart())
@session_manager.connection()
async def start(message: Message, session: AsyncSession, state: FSMContext):
    m = message.from_user
    user: User = await UsersDAO.find_one_or_none(session, GetUserDB(telegram_id=m.id))
    if not user:
        await state.set_state(RegisterUser.started)
        await message.answer("Для начала напишите, как к вам обращаться")
        return
    await message.answer(f"{hello_message}", reply_markup=main_kb)

@dp.message(RegisterUser.started)
async def process_name(message: Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer("Спасибо! Теперь напишите, есть ли у вас противопоказания (например, аллергии или непереносимость). Если противопоказаний нет, напишите 'нет'.")
    await state.set_state(RegisterUser.contra)

@dp.message(RegisterUser.contra)
@session_manager.connection()
async def register_user(message: Message, session: AsyncSession, state: FSMContext):
    await state.update_data(contra=message.text.strip())
    data = await state.get_data()
    await state.clear()

    m = message.from_user
    await UsersDAO.add(session, AddUserDB(telegram_id=m.id, username=m.username, fullname=m.full_name, name=data['name'], contra=data['contra']))
    await message.answer(f"Отлично, {data['name']}! {hello_message}", reply_markup=main_kb)

async def on_startup():
    logger.info("Starting bot...")
    scheduler.add_job(scheduled_task, "interval", minutes=3)
    scheduler.start()

async def on_shutdown():
    logger.info("Shutting down...")
    scheduler.shutdown()
    await dp.storage.close()

async def main():

    dp.include_routers(
        router_recipes,
        router_fridge
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())