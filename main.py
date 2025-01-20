import io
import multiprocessing
import os
import uuid
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, FSInputFile
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command
import asyncio
import aiofiles
import json
import csv
from app.api.dao import UsersDAO
from app.api.models import User
import soundfile as sf
from speech_recognition import Recognizer, AudioFile

from app.create_bot import bot, dp
from app.keyboards.kb import main_kb
# import app.api.utils as ut
from app.api.router import r_user as router_recipes
# from app.schedule.schedule import start_scheduler
from app.api.schemas import GetUserDB, AddUserDB
from app.dao.session_maker import session_manager

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import GigaChatKey
from gigachat import GigaChat


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

# ТЕКСТ | Отправляется в диалог с GigaChat
# @router_main.message(F.text)
# async def handle_text(message: Message):
#     if message.text.strip().lower().startswith('привет'):
#         await message.answer(f"Приветствую тебя и желаю приятной готовки!")
#     elif '713560' in message.text.strip().lower():
#         recipe = ut.load_recipes(True)
#         await message.answer(f"Ты ввёл секретный код! Держи рецепт в подарок {recipe[0]}")
#     else:
#         with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
#             response = giga.chat(message.text)
#             await message.answer(f"GigaChat: {response.choices[0].message.content}")
#             print()

# ДОКУМЕНТ | Загрузка csv, json для добавления рецепта
# @router_main.message(F.document)
# async def handle_document(message: Message, bot: Bot):
#     file_name = f"./docs/{message.document.file_name}"
#     print(file_name)
#     try:
#         await bot.download(message.document, file_name)
        
#         if file_name.endswith(('.csv', '.json')):
#             async with aiofiles.open(file_name, mode='r', encoding='utf-8') as file:
#                 data = await file.read()

#             if file_name.endswith('.csv'):
#                 reader = csv.DictReader(io.StringIO(data), fieldnames=['title', 'ingredients', 'steps'], delimiter=";")
#                 rows = list(reader)
#                 for row in rows:
#                     row['ingredients'] = row['ingredients'].split()
#                     row['steps'] = [row['steps']]
#                     ut.save_recipe(row)
#             elif file_name.endswith('.json'):
#                 recipes = json.loads(data)
#                 for recipe in recipes:
#                     ut.save_recipe(recipe)
                    
#             await message.answer("Файл загружен успешно!")
#         else:
#             await message.answer("Поддерживаются только файлы формата CSV и JSON.")
#     except Exception as e:
#         await message.answer(f"Произошла ошибка при загрузке файла: {e}")

# Транскрибация, отправлять в диалог с GigaChat
# @router_main.message(F.voice)
# async def handle_audio(message: Message):
#     voice_file_id = message.voice.file_id
#     filename = f"{voice_file_id}"
#     await bot.download(voice_file_id, destination=f'{filename}.ogg')

#     data, samplerate = sf.read(f'{filename}.ogg')
#     sf.write(f'{filename}.wav', data, samplerate)

#     os.remove(f'{filename}.ogg')

#     recognizer = Recognizer()
    
#     with AudioFile(f'{filename}.wav') as source:
#         audio_data = recognizer.record(source)

#     try:
#         text = recognizer.recognize_google(audio_data, language="ru-RU")  # Используйте нужный язык
#         await message.reply(f"Текст аудиосообщения: {text}")
#     except Exception as e:
#         await message.reply(f"Произошла ошибка при обработке аудиосообщения: {e}")
    
#     os.remove(f'{filename}.wav')

async def main():
    dp.include_routers(
        router_main,
        router_recipes
    )

    await dp.start_polling(bot)

if __name__ == "__main__":
    # scheduler = multiprocessing.Process(target=start_scheduler())
    # scheduler.start()

    asyncio.run(main())