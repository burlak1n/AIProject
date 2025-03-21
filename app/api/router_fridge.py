import asyncio
import logging
import openai
import base64
import io
from app.api.utils import escape_markdown
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from app.keyboards import kb

from app.api.dao import UsersDAO
from app.api.models import User
from app.api.schemas import GetUserDB
from app.api.utils import image_bytes_to_base64, truncate_message
from app.config import OPENAI_API_KEY, FRIDGE_IMAGE_PROMPT, FOOD_IMAGE_PROMPT, PREFERENCES_TEXT_PROMPT, PROXY
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.session_maker import session_manager

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY
openai.proxy = PROXY  # Указываем прокси



class FridgeImage(StatesGroup):
    waiting_for_fridge_image = State()


class FoodImage(StatesGroup):
    waiting_for_food_image = State()


class IndividualPreferences(StatesGroup):
    waiting_for_preferences_text = State()


# ---------- Создаем Router и регистрируем обработчики ----------
router = Router()


# Обработка колбэков от кнопок
@router.callback_query(lambda c: c.data in ["fridge", "food", "preferences"])
async def process_menu(callback_query: types.CallbackQuery, state: FSMContext) -> None:
    selection = callback_query.data
    if selection == "fridge":
        await callback_query.message.answer("Отправьте, пожалуйста, фотографию своего холодильника.")
        await state.set_state(FridgeImage.waiting_for_fridge_image)
    elif selection == "food":
        await callback_query.message.answer(
            "Отправьте, пожалуйста, фотографию еды, чтобы я мог определить, что это и как её приготовить.")
        await state.set_state(FoodImage.waiting_for_food_image)
    elif selection == "preferences":
        await callback_query.message.answer(
            "Расскажите о своих индивидуальных предпочтениях в еде. Опишите, что нравится, а что нет, или укажите продукты, которые у вас есть.")
        await state.set_state(IndividualPreferences.waiting_for_preferences_text)
    await callback_query.answer()


# -------------------- Вызов GPT-4o с изображением (через base64) --------------------
def call_gpt4o_with_image(system_prompt: str, user_text: str, base64_image: str) -> str:
    """
    Функция отправляет сообщение модели 'gpt-4o'
    с текстом и base64-картинкой.
    """
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Произошла ошибка при обращении к GPT-4o: {e}"


# ------------------ Получение файла из Telegram в виде байт (без сохранения на диск) ------------------
async def get_telegram_file_bytes(photo: types.PhotoSize, bot: Bot) -> bytes:
    """
    Загружает файл с серверов Telegram и возвращает его содержимое в виде байт.
    """
    file_info = await bot.get_file(photo.file_id)
    bio = io.BytesIO()
    await bot.download_file(file_info.file_path, destination=bio)
    bio.seek(0)
    return bio.read()


# ------------------ Обработчики фотографий ------------------
@router.message(FridgeImage.waiting_for_fridge_image, F.content_type == ContentType.PHOTO)
@session_manager.connection()
async def handle_fridge_image(message: types.Message, session: AsyncSession, state: FSMContext) -> None:
    """
    Получаем фото холодильника, обрабатываем в памяти,
    передаём в GPT-4o с использованием FRIDGE_IMAGE_PROMPT.
    """
    await message.answer("Секундочку, обрабатываю фото вашего холодильника...")

    photo = message.photo[-1]
    image_bytes = await get_telegram_file_bytes(photo, message.bot)
    base64_image = image_bytes_to_base64(image_bytes)

    # Получаем пользователя из БД
    m = message.from_user
    user: User = await UsersDAO.find_one_or_none(session, GetUserDB(telegram_id=m.id))
    if not user:
        await message.answer("Ошибка: пользователь не найден")
        return

    contra = user.contra if user.contra is not None else "Нет противопоказаний"
    user_text = f"Вот фото моего холодильника. Противопоказания: {contra}. Что можно приготовить?"

    response_text = call_gpt4o_with_image(FRIDGE_IMAGE_PROMPT, user_text, base64_image)
    response_text = truncate_message(response_text)


    await message.answer(escape_markdown(response_text),reply_markup=kb.main_kb)
    await state.clear()


@router.message(FoodImage.waiting_for_food_image, F.content_type == ContentType.PHOTO)
@session_manager.connection()
async def handle_food_image(message: types.Message, session: AsyncSession, state: FSMContext) -> None:
    """
    Получаем фото блюда, обрабатываем в памяти,
    передаём в GPT-4o с использованием FOOD_IMAGE_PROMPT для опознания.
    """
    await message.answer("Секундочку, пытаюсь определить, что за блюдо на фото...")

    photo = message.photo[-1]
    image_bytes = await get_telegram_file_bytes(photo, message.bot)
    base64_image = image_bytes_to_base64(image_bytes)

    # Получаем пользователя из БД
    m = message.from_user
    user: User = await UsersDAO.find_one_or_none(session, GetUserDB(telegram_id=m.id))
    if not user:
        await message.answer("Ошибка: пользователь не найден")
        return

    contra = user.contra if user.contra is not None else "Нет противопоказаний"
    user_text = f"Вот фото блюда. Противопоказания: {contra}. Что это за блюдо и как его приготовить?"

    response_text = call_gpt4o_with_image(FOOD_IMAGE_PROMPT, user_text, base64_image)
    response_text = truncate_message(response_text)

    await message.answer(escape_markdown(response_text),reply_markup=kb.main_kb)
    await state.clear()


@router.message(IndividualPreferences.waiting_for_preferences_text)
@session_manager.connection()
async def handle_preferences_text(message: types.Message, session: AsyncSession, state: FSMContext) -> None:
    """
    Обрабатываем текстовые предпочтения с использованием PREFERENCES_TEXT_PROMPT.
    """
    await message.answer("Обрабатываю ваши предпочтения, подождите...")

    # Получаем пользователя из БД
    m = message.from_user
    user: User = await UsersDAO.find_one_or_none(session, GetUserDB(telegram_id=m.id))
    if not user:
        await message.answer("Ошибка: пользователь не найден")
        return

    contra = user.contra if user.contra is not None else ""
    user_input = message.text.strip()

    prompt = (
        f"{PREFERENCES_TEXT_PROMPT}\n"
        f"Пользовательские предпочтения: {user_input}\n"
        f"Противопоказания: {contra}\n"
        "Задача: предложить блюда, подходящие под указанные предпочтения с учётом имеющихся продуктов."
    )
    response_text = call_gpt_api(prompt)
    response_text = truncate_message(response_text)
    await message.answer(escape_markdown(response_text),reply_markup=kb.main_kb)
    await state.clear()


# ------------------ Функция для работы с текстовой моделью (например, o3-mini) ------------------
def call_gpt_api(prompt: str) -> str:
    """
    Функция для обращения к текстовой модели (например, o3-mini)
    """
    try:
        response = openai.ChatCompletion.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": PREFERENCES_TEXT_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Произошла ошибка при обращении к ИИ: {e}"