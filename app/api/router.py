from datetime import datetime
import os
import random
from typing import List
import uuid
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, CallbackQuery, InputFile, BufferedInputFile
from gigachat import GigaChat
from loguru import logger
from app.api.dao import UsersDAO, RecipesDAO
from app.api.middleware import AuthMiddleware
from app.dao.session_maker import session_manager
from app.api.models import User, Recipe
from app.api.schemas import GetRecipeDB, AddRecipeDB
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from app.api.utils import find_similar_recipes, create_tfidf_vectors, text_to_speech
from app.config import GigaChatKey, kandinsky_api_key, kandinsky_secret_key
from gigachat.models import Chat, Messages, MessagesRole
from app.create_bot import bot
import soundfile as sf
from speech_recognition import Recognizer, AudioFile
from kandinskylib import Kandinsky
import io
import re

r_user = Router()
r_user.message.middleware(AuthMiddleware())

class RecipeStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_ingredients = State()
    waiting_for_steps = State()
    
class Payload(StatesGroup):
    payload = State()

class Image(StatesGroup):
    image = State()
    
@r_user.callback_query(F.data == "image")
async def kandin_image(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Image.image)
    await callback.message.reply("Введите сообщение, по которому Kandinsky сгенерирует фотографию")

@r_user.message(Image.image)
async def kandin_gen_image(message:Message, state: FSMContext):
    await state.update_data(image=message.text)
    data = await state.get_data()

    client = Kandinsky(kandinsky_api_key, kandinsky_secret_key)
    p = f"docs/{uuid.uuid4()}.jpg"
    _ = client.generate_image(
        prompt = data['image'],
        scale="1:1",
        style="UHD",
        path=p
    )

    await message.answer_photo(FSInputFile(p))
    os.remove(p)
    await state.clear()

# @r_user.callback_query(F.data == "help")
# async def cmd_help(callback: CallbackQuery):
#     await callback.answer()
#     await callback.message.answer(command_list_message, parse_mode="Markdown")

# Команда /add_recipe
@r_user.callback_query(F.data == "add_recipe")
async def add_recipe(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(RecipeStates.waiting_for_title)
    await callback.message.answer("Введите название рецепта:")

# Ожидание названия рецепта
@r_user.message(RecipeStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    
    await state.set_state(RecipeStates.waiting_for_ingredients)
    await message.answer("Отлично! Теперь напишите ингредиенты через запятую.")

# Ожидание ингредиентов
@r_user.message(RecipeStates.waiting_for_ingredients)
async def process_ingredients(message: Message, state: FSMContext):
    await state.update_data(ingridiends=message.text.split(','))

    await state.set_state(RecipeStates.waiting_for_steps)
    await message.answer("Теперь опишите шаги приготовления.")

# Завершение добавления рецепта
@r_user.message(RecipeStates.waiting_for_steps)
@session_manager.connection()
async def finish_adding_recipe(message: Message, state: FSMContext, session: AsyncSession, user: User):
    data = await state.get_data()
    data['steps'] = message.text.split('\n')

    a = AddRecipeDB(user_id=user.id, title=data["title"], ingridiends=data["ingridiends"], steps=data["steps"])
    recipe: Recipe = await RecipesDAO.add(session, a)
    
    await message.answer(f"Рецепт '{recipe.title}' успешно добавлен!")
    await state.clear()

@r_user.callback_query(F.data == "random_me")
@session_manager.connection()
async def get_random_recipe(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    recipes: List[Recipe] = await RecipesDAO.find_all(session, GetRecipeDB(user_id=user.id))
    if not recipes:
        await callback.message.answer("У вас еще нет рецептов. Добавьте их с помощью команды /add_recipe.")
        return 
    
    recipe = random.choice(recipes)
    await callback.message.answer(str(recipe))

@r_user.callback_query(F.data == "recipes")
@session_manager.connection()
async def get_recipes(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    recipes: List[Recipe] = await RecipesDAO.find_all(session, GetRecipeDB(user_id=user.id))
    if not recipes:
        await callback.message.answer("У вас еще нет рецептов! Добавьте их с помощью команды /add_recipe")
        return

    await callback.message.answer("Ваши рецепты:")

    for recipe in recipes:
        await callback.message.answer(str(recipe))

@r_user.callback_query(F.data == "privacy")
@session_manager.connection()
async def change_privace(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    user = await UsersDAO.find_by_ids(session, [user.id])
    user = user[0]
    user.private = not user.private
    await session.commit()
    await callback.message.answer(f"Ваша приватность изменена на {user.private}")

@r_user.callback_query(F.data == "find")
@session_manager.connection()
async def find_recipes(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    msg = callback.data.split(maxsplit=1)
    if len(msg) > 1:
        recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session=session, user_id=user.id)
        if not recipes:
            await callback.message.answer("В Базе пока нет рецептов!")
            return
        tfidf_matrix, vectorizer = await create_tfidf_vectors(recipes)
        for recipe in await find_similar_recipes(msg[1], recipes, tfidf_matrix, vectorizer):
            await callback.message.reply(str(recipe))
    else:
        await callback.message.reply("Укажите ингредиент после команды /find.")

@r_user.callback_query(F.data == "random")
@session_manager.connection()
async def random_others_recipe(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session, user_id=user.id)
    if not recipes:
        await callback.message.answer("В Базе пока нет рецептов!")
        return
    recipe = random.choice(recipes)
    await callback.message.answer(str(recipe))

@r_user.callback_query(F.data == "giga")
async def handle_text(callback: CallbackQuery, state:FSMContext):
    await callback.answer()
    await state.set_state(Payload.payload)
    await state.update_data(payload=Chat(
        messages=[
            Messages(
                role=MessagesRole.SYSTEM,
                content="Ты профессиональный повар, который готов посоветовать множестнов рецептов"
            )
        ],
        temperature=0.7,
        max_tokens=100,
    ))
    await callback.message.answer("Чем могу помочь?")
            
# ГОЛОСОВОЕ | GigaChat
@r_user.message(F.voice, Payload.payload)
async def handle_audio(message: Message, state:FSMContext):
    logger.info("handle_audio")
    voice_file_id = message.voice.file_id
    
    # Скачиваем файл в память
    voice_file = await bot.download(voice_file_id)
    voice_bytes = voice_file.read()
    
    # Конвертируем ogg в wav в памяти
    with io.BytesIO(voice_bytes) as ogg_buffer:
        data, samplerate = sf.read(ogg_buffer)
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, data, samplerate, format='wav')
        wav_buffer.seek(0)
        
        recognizer = Recognizer()
        with AudioFile(wav_buffer) as source:
            audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data, language="ru-RU")  # Используйте нужный язык
        logger.info(f"Вы сказали: {text}")
        with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
            data = await state.get_data()
            payload = data["payload"]
            
            payload.messages.append(Messages(role=MessagesRole.USER, content=text))
            response = giga.chat(payload)
            payload.messages.append(response.choices[0].message)
            await state.update_data(payload=payload)
            
            # Преобразуем ответ в голосовое сообщение
            response_text = response.choices[0].message.content
            # Убираем Markdown форматирование
            response_text = re.sub(r'[*_`#]', '', response_text)
            audio = await text_to_speech(response_text)
            
            # Используем BufferedInputFile
            voice = BufferedInputFile(audio.getvalue(), filename="response.ogg")
            await message.answer_voice(voice)
            
    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке аудиосообщения: {e}")

# ТЕКСТ | GigaChat
@r_user.message(Payload.payload)
async def handle_giga(message: Message, state:FSMContext):
    if message.text.strip().lower().startswith('привет'):
            await message.answer(f"Приветствую тебя и желаю приятной готовки!")
    else:
        await bot.send_chat_action(message.chat.id, "typing")
        with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
            data = await state.get_data()
            payload = data["payload"]
            
            payload.messages.append(Messages(role=MessagesRole.USER, content=message.text))
            response = giga.chat(payload)
            payload.messages.append(response.choices[0].message)
            await state.update_data(payload=payload)
            await message.answer(f"{response.choices[0].message.content}")

@session_manager.connection()
async def scheduled_task(session:AsyncSession):
    users: List[User] = await UsersDAO.find_all(session, None)
    with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
        response = giga.chat("Сгенерируй новое, короткое, ежедневное, мотивирующее сообщение для начинающих поваров")
        for user in users:
            await bot.send_message(user.telegram_id, text=response.choices[0].message.content)

            user.updated_at = datetime.now()
            await session.commit()
