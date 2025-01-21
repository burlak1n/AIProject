from datetime import datetime
import os
import random
from typing import List
import uuid
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from gigachat import GigaChat
from app.api.dao import UsersDAO, RecipesDAO
from app.api.middleware import AuthMiddleware
from app.dao.session_maker import session_manager
from app.api.models import User, Recipe
from app.api.schemas import GetRecipeDB, AddRecipeDB
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from .utils import find_similar_recipes, create_tfidf_vectors
from app.config import GigaChatKey, kandinsky_api_key, kandinsky_secret_key
from gigachat.models import Chat, Messages, MessagesRole
from app.create_bot import bot
import soundfile as sf
from speech_recognition import Recognizer, AudioFile
from kandinskylib import Kandinsky

r_user = Router()
r_user.message.middleware(AuthMiddleware())

class Payload(StatesGroup):
    payload = State()

command_list_message = \
'''
Команды:
/start - регистрация
/help - перечисление всех функций бота
/recipes - список всех рецептов
/add_recipe - добавить новый рецепт
/random_recipe - получить случайный рецепт
/find ... - по запросу найти похожий рецепт из базы

Прочее:
текст - ответит GigaChat
голосовое - транскрибируется и отправится как сообщение для GigaChat
.csv - запись рецепта (Формат:"Название,продукт1,продукт2,'Шаг1,Шаг2,Шаг3'")
'''

class RecipeStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_ingredients = State()
    waiting_for_steps = State()


class Image(StatesGroup):
    image = State()
    
@r_user.message(Command("image"))
async def name_menu(message:Message, state: FSMContext):
    await state.set_state(Image.image)
    await message.reply("Введите сообщение, по которому Kandinsky сгенерирует фотографию")

@r_user.message(Image.image)
async def get_name(message:Message, state: FSMContext):
    await state.update_data(image=message.text)
    data = await state.get_data()

    client = Kandinsky(kandinsky_api_key, kandinsky_secret_key)
    p = f"./image/{uuid.uuid4()}.jpg"
    _ = client.generate_image(
        prompt = data['image'],
        scale="1:1",
        style="UHD",
        path=p
    )

    await message.answer_photo(FSInputFile(p))
    os.remove(p)
    await state.clear()

@r_user.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(command_list_message)

# Команда /add_recipe
@r_user.message(Command("add_recipe"))
async def add_recipe(message: Message, state: FSMContext):
    await state.set_state(RecipeStates.waiting_for_title)
    await message.answer("Введите название рецепта:")

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

@r_user.message(Command("random_me"))
@session_manager.connection()
async def get_random_recipe(message: Message, session: AsyncSession, user: User):
    recipes: List[Recipe] = await RecipesDAO.find_all(session, GetRecipeDB(user_id=user.id))
    if not recipes:
        await message.answer("У вас еще нет рецептов. Добавьте их с помощью команды /add_recipe.")
        return 
    
    recipe = random.choice(recipes)
    await message.answer(str(recipe))

@r_user.message(Command("recipes"))
@session_manager.connection()
async def get_recipes(message: Message, session: AsyncSession, user: User):
    recipes: List[Recipe] = await RecipesDAO.find_all(session, GetRecipeDB(user_id=user.id))
    if not recipes:
        await message.answer("У вас еще нет рецептов! Добавьте их с помощью команды /add_recipe")
        return

    await message.answer("Ваши рецепты:")

    for recipe in recipes:
        await message.answer(str(recipe))

@r_user.message(Command("privacy"))
@session_manager.connection()
async def change_privace(message: Message, session: AsyncSession, user: User):
    user = await UsersDAO.find_by_ids(session, [user.id])
    user = user[0]
    user.private = not user.private
    await session.commit()
    await message.answer(f"Ваша приватность изменена на {user.private}")

@r_user.message(Command("find"))
@session_manager.connection()
async def name_menu(message:Message, session: AsyncSession, user: User):
    recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session, user_id=user.id)
    tfidf_matrix, vectorizer = await create_tfidf_vectors(recipes)

    msg = message.text.split(maxsplit=1)
    if len(msg) > 1:
        print(msg[1])
        for recipe in await find_similar_recipes(msg[1], recipes, tfidf_matrix, vectorizer):
            await message.reply(str(recipe))
    else:
        await message.reply("Укажите ингредиент после команды /find.")

@r_user.message(Command("random"))
@session_manager.connection()
async def random_others_recipe(message:Message, session: AsyncSession, user: User):
    recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session, user_id=user.id)
    if not recipes:
        await message.answer("В Базе пока нет рецептов!")
        return
    recipe = random.choice(recipes)
    await message.answer(str(recipe))

# ТЕКСТ | GigaChat
@r_user.message(Command("giga"))
async def handle_text(message: Message, state:FSMContext):
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
    await message.answer("Чем могу помочь?")
            
# ГОЛОСОВОЕ | GigaChat
@r_user.message(F.voice, Payload.payload)
async def handle_audio(message: Message, state:FSMContext):
    voice_file_id = message.voice.file_id
    filename = f"{voice_file_id}"
    await bot.download(voice_file_id, destination=f'{filename}.ogg')

    data, samplerate = sf.read(f'{filename}.ogg')
    sf.write(f'{filename}.wav', data, samplerate)

    os.remove(f'{filename}.ogg')

    recognizer = Recognizer()
    
    with AudioFile(f'{filename}.wav') as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data, language="ru-RU")  # Используйте нужный язык
        with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
            data = await state.get_data()
            payload = data["payload"]
            
            payload.messages.append(Messages(role=MessagesRole.USER, content=message.text))
            response = giga.chat(payload)
            payload.messages.append(response.choices[0].message)
            await state.update_data(payload=payload)
            print("Bot: ", response.choices[0].message.content)
        await message.reply(f"Текст аудиосообщения: {text}")
    except Exception as e:
        await message.reply(f"Произошла ошибка при обработке аудиосообщения: {e}")
    
    os.remove(f'{filename}.wav')

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
            await message.answer(f"Bot: {response.choices[0].message.content}")

@session_manager.connection()
async def scheduled_task(session:AsyncSession):
    users: List[User] = await UsersDAO.find_all(session, None)
    with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
        response = giga.chat("Сгенерируй короткое, ежедневное, мотивирующее сообщение для начинающих поваров")
        for user in users:
            await bot.send_message(user.id, text=response.choices[0].message.content)

            user.updated_at = datetime.now()
            await session.commit()
