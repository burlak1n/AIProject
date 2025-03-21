from datetime import datetime
import os
import random
from typing import List
import uuid
from app.keyboards import kb
from aiogram import F, Router
from aiogram.types import Message, FSInputFile, CallbackQuery, BufferedInputFile
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

global temp_recipe


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

# Инициализация GigaChat
async def init_giga_chat():
    return Chat(
        messages=[
            Messages(
                role=MessagesRole.SYSTEM,
                content="Ты профессиональный повар, который готов посоветовать множество рецептов. В начале каждого рецепта ОБЯЗАТЕЛЬНО напиши его название, затем уже сам рецепт. Всегда начинай любой рецепт с его названия целиком"
            )
        ],
        temperature=0.7,
        max_tokens=1000,
    )

async def init_giga_chat_calculate_ingredients():
    return Chat(
        messages=[
            Messages(
                role=MessagesRole.SYSTEM,
                content="Ты профессиональный повар и математик. Ты потрясающи считаешь порции. Рассчитай, сколько ингредиентов нужно пользователю. Если пользователь указал количество порций, то необходимо умножить количество каждого ингредиента на количество порций. Отвечай крато и по делу."
            )
        ],
        temperature=1,
        max_tokens=1000,
    )

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
async def calculate_ingredients(message: Message):

    # Извлекаем текст запроса
    user_input = message.text

    # Инициализируем GigaChat
    with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
        # Формируем запрос
        payload = await init_giga_chat_calculate_ingredients()
        payload.messages.append(Messages(role=MessagesRole.USER, content=user_input))

        # Отправляем запрос к GigaChat
        response = giga.chat(payload)

        # Отправляем ответ пользователю
        await message.answer(response.choices[0].message.content, reply_markup=kb.menu_kb)

class Image(StatesGroup):
    image = State()

# @r_user.callback_query(F.data == "image")
# async def kandin_image(callback: CallbackQuery, state: FSMContext):
#     await callback.answer()
#     await state.set_state(Image.image)
#     await callback.message.reply("Введите сообщение, по которому Kandinsky сгенерирует фотографию")

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

    await message.answer(f"Рецепт '{recipe.title}' успешно добавлен!", reply_markup=kb.menu_kb)
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
        await callback.message.answer(f"Ваши рецепты видны другим пользователям", reply_markup=kb.main_kb)
    else:
        await callback.message.answer(f"Ваши рецепты не видны другим пользователям", reply_markup=kb.main_kb)
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
        await callback.message.reply("Укажите ингредиент после команды /find.", reply_markup=kb.menu_kb)

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
#     await state.set_state(Payload.payload)
#     await state.update_data(payload=Chat(
#         messages=[
#             Messages(
#                 role=MessagesRole.SYSTEM,
#                 content="Ты профессиональный повар, который готов посоветовать множестнов рецептов"
#             )
#         ],
#         temperature=0.7,
#         max_tokens=1000,
#     ))
    await callback.message.answer("Чем могу помочь?")

# ГОЛОСОВОЕ | GigaChat
@r_user.message(F.voice)
async def handle_audio(message: Message, state: FSMContext):
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
        # Распознаем текст из аудио
        text = recognizer.recognize_google(audio_data, language="ru-RU")  # Используйте нужный язык
        logger.info(f"Вы сказали: {text}")

        # Получаем данные из состояния
        data = await state.get_data()

        # Если payload не существует, инициализируем его
        if "payload" not in data:
            payload = await init_giga_chat()
        else:
            payload = data["payload"]

        # Добавляем сообщение пользователя в историю
        payload.messages.append(Messages(role=MessagesRole.USER, content=text))

        # Отправляем запрос к GigaChat
        with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
            response = giga.chat(payload)

            # Сохраняем обновлённый payload в состоянии
            payload.messages.append(response.choices[0].message)
            await state.update_data(payload=payload)

            # Преобразуем ответ в голосовое сообщение
            response_text = response.choices[0].message.content
            # Убираем Markdown форматирование
            response_text = re.sub(r'[*_`#]', '', response_text)
            audio, duration = await text_to_speech(response_text)

            # Используем BufferedInputFile
            voice = BufferedInputFile(audio.getvalue(), filename="response.ogg")

            # Отправляем голосовое сообщение
            await message.answer_voice(voice=voice, duration=duration, reply_markup=kb.menu_kb)

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
@r_user.message(F.text)
async def handle_text(message: Message, state: FSMContext):
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
        data["payload"] = await init_giga_chat()

    # Добавляем сообщение пользователя в историю
    data["payload"].messages.append(Messages(role=MessagesRole.USER, content=message.text))

    # Отправляем запрос к GigaChat
    with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
        response = giga.chat(data["payload"])
        data["payload"].messages.append(response.choices[0].message)
        await state.update_data(payload=data["payload"])

        global temp_recipe

        temp_recipe = response.choices[0].message.content[:100]

        # Отправляем ответ пользователю
        await message.answer(response.choices[0].message.content, reply_markup=kb.illustrate_kb)
