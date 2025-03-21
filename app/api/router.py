from datetime import datetime
import os
import random
from typing import List
import uuid
from app.keyboards import kb
from aiogram import F, Router
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
from loguru import logger
from app.api.utils import escape_markdown
from app.api.dao import UsersDAO, RecipesDAO
from app.api.middleware import AuthMiddleware
from app.dao.session_maker import session_manager
from app.api.models import User, Recipe
from app.api.schemas import GetRecipeDB, AddRecipeDB, GetUserDB
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from app.api.utils import find_similar_recipes, create_tfidf_vectors, generate_text, init_giga_chat, init_giga_chat_calculate_ingredients, text_to_speech
from app.config import kandinsky_api_key, kandinsky_secret_key
from app.create_bot import bot
import soundfile as sf
from speech_recognition import Recognizer, AudioFile
from kandinskylib import Kandinsky
import io
import re

r_user = Router()

global temp_recipe

motivation_payload = None

r_user.message.middleware(AuthMiddleware())
r_user.callback_query.middleware(AuthMiddleware())

class RecipeStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_ingredients = State()
    waiting_for_steps = State()

class CalculateIngredients(StatesGroup):
    waiting_for_ingredients = State()

class Payload(StatesGroup):
    payload = State()

# Обработка текстовых сообщений

@r_user.callback_query(F.data == "calculate_ingredients")
async def process_calculating_ingredients(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CalculateIngredients.waiting_for_ingredients)
    await callback.message.reply("Напишите рецепт, по которому нужно рассчитать ингредиенты")

@r_user.callback_query(F.data == "menu")
async def process_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Что вы хотите сделать?", reply_markup=kb.main_kb)

# Обработчик для расчета ингредиентов
@r_user.message(CalculateIngredients.waiting_for_ingredients)
async def calculate_ingredients(message: Message, user: User):
    payload = await init_giga_chat_calculate_ingredients(user.contra)

    # TODO: Запись payload в состояние
    answer, payload = await generate_text(message.text, payload)

    # Отправляем ответ пользователю
    await message.answer(escape_markdown(answer), reply_markup=kb.menu_kb)

class Image(StatesGroup):
    image = State()

@r_user.callback_query(F.data == "image")
async def kandin_gen_image(callback: CallbackQuery, state: FSMContext):
    # await state.update_data(image=message.text)
    await callback.answer()
    await callback.message.answer("Создаю иллюстрацию")

    prompt = f"Проиллюстрируй этот рецепт: {str(temp_recipe)}"
    print(prompt)
    client = Kandinsky(kandinsky_api_key, kandinsky_secret_key)
    p = f"docs/{uuid.uuid4()}.jpg"
    _ = client.generate_image(
        prompt = prompt,
        scale="1:1",
        style="UHD",
        path=p
    )

    await callback.message.answer_photo(FSInputFile(p), reply_markup=kb.menu_kb)
    os.remove(p)
    await state.clear()

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

    await message.answer(f"Рецепт '{recipe.title}' успешно добавлен!", reply_markup=kb.main_kb)
    await state.clear()

@r_user.callback_query(F.data == "random_me")
@session_manager.connection()
async def get_random_recipe(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    recipes: List[Recipe] = await RecipesDAO.find_all(session, GetRecipeDB(user_id=user.id))
    if not recipes:
        await callback.message.answer("У вас еще нет рецептов. Добавьте их с помощью команды /add_recipe.", reply_markup=kb.menu_kb)
        return

    recipe = random.choice(recipes)
    await callback.message.answer(str(recipe), reply_markup=kb.menu_kb)

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
        await callback.message.answer(str(recipe), reply_markup=kb.menu_kb)

@r_user.callback_query(F.data == "privacy")
@session_manager.connection()
async def change_privace(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    user = await UsersDAO.find_by_ids(session, [user.id])
    user = user[0]
    user.private = not user.private
    await session.commit()
    if user.private:
        await callback.message.edit_text(f"Ваши рецепты видны другим пользователям", reply_markup=kb.main_kb)
    else:
        await callback.message.edit_text(f"Ваши рецепты не видны другим пользователям", reply_markup=kb.main_kb)
    # await callback.message.answer(f"Ваша приватность изменена на {user.private}")

@r_user.callback_query(F.data == "find")
@session_manager.connection()
async def find_recipes(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    msg = callback.data.split(maxsplit=1)
    if len(msg) > 1:
        recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session=session, user_id=user.id)
        if not recipes:
            await callback.message.answer("В Базе пока нет рецептов!", reply_markup=kb.menu_kb)
            return
        tfidf_matrix, vectorizer = await create_tfidf_vectors(recipes)
        for recipe in await find_similar_recipes(msg[1], recipes, tfidf_matrix, vectorizer):
            await callback.message.reply(str(recipe))
    else:
        await callback.message.reply(escape_markdown("Укажите ингредиент после команды /find."), reply_markup=kb.menu_kb)

@r_user.callback_query(F.data == "random")
@session_manager.connection()
async def random_others_recipe(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session, user_id=user.id)
    if not recipes:
        await callback.message.answer("В Базе пока нет рецептов!", reply_markup=kb.menu_kb)
        return
    recipe = random.choice(recipes)
    await callback.message.answer(str(recipe), reply_markup=kb.menu_kb)

@r_user.callback_query(F.data == "giga")
async def handle_text(callback: CallbackQuery, state:FSMContext):
    await callback.answer()
    await callback.message.answer("Чем могу помочь?")

# ГОЛОСОВОЕ | GigaChat
@r_user.message(F.voice)
async def handle_audio(message: Message, state: FSMContext, user: User):
    try:
        # Скачиваем и конвертируем аудио
        voice_file = await bot.download(message.voice.file_id)
        
        # Конвертируем OGG в WAV
        with io.BytesIO() as wav_buffer:
            data, samplerate = sf.read(voice_file)
            sf.write(wav_buffer, data, samplerate, format='wav')
            wav_buffer.seek(0)
            
            # Распознаем текст
            recognizer = Recognizer()
            with AudioFile(wav_buffer) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language="ru-RU")
        
        logger.info(f"Распознанный текст: {text}")

        await bot.send_chat_action(message.chat.id, "record_voice")
        # Обработка через GigaChat
        data = await state.get_data()

        payload = data.get("payload") or await init_giga_chat(user.contra)
        answer, payload = await generate_text(text, payload)
        
        if "payload" not in data:
            await state.update_data(payload=payload)

        # Генерация и отправка ответа
        response_text = re.sub(r'[*_`#]', '', answer)
        audio, duration = await text_to_speech(response_text)
        
        await message.answer_voice(
            voice=BufferedInputFile(audio.getvalue(), filename="response.ogg"),
            duration=duration,
            reply_markup=kb.menu_kb
        )

    except Exception as e:
        logger.error(f"Ошибка обработки аудио: {e}")
        await message.answer(f"Произошла ошибка при обработке аудиосообщения: {e}")
        

@session_manager.connection()
async def scheduled_task(session:AsyncSession):
    users: List[User] = await UsersDAO.find_all(session, None)
    # Отправляем запрос к GigaChat
    prompt = "Сгенерируй новое, короткое, ежедневное, мотивирующее сообщение для начинающих поваров"
    
    global motivation_payload

    answer, motivation_payload = await generate_text(prompt, motivation_payload)
    
    for user in users:
        await bot.send_message(user.telegram_id, text=escape_markdown(answer))

        user.updated_at = datetime.now()
        await session.commit()

@r_user.message(F.text)
async def handle_text(message: Message, state: FSMContext, user: User):
    current_state = await state.get_state()

    # Состояния, при которых GigaChat не должен обрабатывать сообщения
    skip_states = [
        RecipeStates.waiting_for_title,
        RecipeStates.waiting_for_ingredients,
        RecipeStates.waiting_for_steps
    ]

    # Если текущее состояние в списке skip_states, пропускаем GigaChat
    if current_state in skip_states:
        return


    # Проверяем, является ли сообщение командой
    if message.text.startswith('/'):
        # Если это команда, пропускаем обработку GigaChat
        return

    await state.set_state(Payload.payload)

    # Если это не команда, обрабатываем через GigaChat
    await bot.send_chat_action(message.chat.id, "typing")  # Показываем, что бот печатает
    data = await state.get_data()

    # Инициализируем GigaChat, если это первый запрос
    if "payload" not in data:
        data["payload"] = await init_giga_chat(user.contra)

    # Отправляем запрос к GigaChat
    answer, payload = await generate_text(message.text, data["payload"])
    await state.update_data(payload = payload)

    global temp_recipe

    temp_recipe = answer[:100]

    # Отправляем ответ пользователю
    await message.answer(escape_markdown(answer), reply_markup=kb.illustrate_kb)
