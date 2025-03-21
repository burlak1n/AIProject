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

hello_message = \
'''
🍳 *Основные функции бота* 🍳

📸 *Работа с изображениями:*
\\- Рецепт из холодильника 🍳 \\- отправьте фото, получите рецепты
\\- Определить блюдо 🍔 \\- отправьте фото, узнайте что это и как приготовить

📝 *Индивидуальные предпочтения:*
\\- Предпочтения 💕 \\- расскажите о своих вкусах, получите персонализированные рекомендации

📚 *Работа с рецептами:*
\\- Добавить рецепт 🗒️ \\- пошаговое добавление нового рецепта
\\- Рецепты 📕 \\- просмотр всех ваших рецептов
\\- Случайный рецепт 👁️ \\- случайный выбор из вашей коллекции
\\- Рассчитай ингредиенты 🧮 \\- расчет количества ингредиентов для нужного числа порций

🤖 *Интеллектуальные функции:*
\\- Спросить у помощника 🙋‍♂️ \\- диалог с кулинарным помощником
\\- Проиллюстрировать рецепт 🖼️ \\- создание изображения будущего блюда

💡 *Прочее:*
\\- Отправьте текст: Интеллектуальный помощник ответит на ваш кулинарный вопрос
\\- Отправьте голосовое сообщение: помощник ответит вам голосом
'''
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
    await message.answer(hello_message, parse_mode='MarkdownV2', reply_markup=main_kb)

@dp.message(RegisterUser.started)
async def process_name(message: Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer("Спасибо! Теперь напишите, есть ли у вас противопоказания (например, аллергии или непереносимость). Если противопоказаний нет, напишите 'нет'.")
    await state.set_state(RegisterUser.contra)

@dp.message(RegisterUser.contra)
@session_manager.connection()
async def register_user(message: Message, session: AsyncSession, state: FSMContext):
    logger.info(f"Начало регистрации пользователя {message.from_user.id}")
    
    try:
        # Логируем получение противопоказаний
        contra = message.text.strip()
        logger.debug(f"Получены противопоказания: {contra}")
        await state.update_data(contra=contra)
        
        # Получаем данные из состояния
        data = await state.get_data()
        logger.debug(f"Данные пользователя: {data}")
        await state.clear()

        m = message.from_user
        logger.info(f"Добавление пользователя в БД: ID={m.id}, username={m.username}")

        # Добавляем пользователя в БД
        user_data = AddUserDB(
            telegram_id=m.id,
            username=m.username,
            fullname=m.full_name,
            name=data['name'],
            contra=data['contra']
        )
        await UsersDAO.add(session, user_data)
        
        # Отправляем приветственное сообщение
        logger.info(f"Отправка приветственного сообщения пользователю {m.id}")
        await message.answer(f"Отлично, {data['name']}! {hello_message}", reply_markup=main_kb)
        
        logger.info(f"Пользователь {m.id} успешно зарегистрирован")
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте снова.")
        raise

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
        router_fridge,
        router_recipes
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())