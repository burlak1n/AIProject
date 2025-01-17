import random
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.api.dao import UsersDAO, RecipesDAO
from app.dao.session_maker import session_manager
from app.api.models import User
from app.api.schemas import GetUserDB, UserIDDB
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

r = Router()

class RecipeStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_ingredients = State()
    waiting_for_steps = State()

# Команда /add_recipe
@r.message(Command("add_recipe"))
async def add_recipe(message: Message, state: FSMContext):
    await state.set_state(RecipeStates.waiting_for_title)
    await message.answer("Пожалуйста, введите название рецепта:")

# Ожидание названия рецепта
@r.message(RecipeStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    
    await state.set_state(RecipeStates.waiting_for_ingredients)
    await message.answer("Отлично! Теперь напишите ингредиенты через запятую.")

# Ожидание ингредиентов
@r.message(RecipeStates.waiting_for_ingredients)
async def process_ingredients(message: Message, state: FSMContext):
    await state.update_data(message.text.split(','))

    await state.set_state(RecipeStates.waiting_for_steps)
    await message.answer("Теперь опишите шаги приготовления.")

# Завершение добавления рецепта
@r.message(RecipeStates.waiting_for_steps)
async def finish_adding_recipe(message: Message, state: FSMContext):
    data = await state.get_data()
    data['steps'] = message.text.split('\n')

    # data -> schema -> db
    # Сохранение рецепта в файл
    save_recipe(data)
    
    await message.answer(f"Рецепт '{data['title']}' успешно добавлен!")
    await state.clear()


@r.message(Command("random_recipe"))
@session_manager.connection(commit=True)
async def get_random_recipe(message: Message, session: AsyncSession):
    user_schema = GetUserDB(telegram_id=message.from_user.id)
    user: User = await UsersDAO.find_one_or_none(session, user_schema)
    recipes = await RecipesDAO.find_all(session, UserIDDB(user_id=user.id))
    if not recipes:
        await message.answer("У вас еще нет рецептов. Добавьте их с помощью команды /add_recipe.")
        return 
    
    recipe = random.choice(recipes)
    await message.answer(recipe)

# Добавить Middleware для зарегестрированных пользователей, передавая объект пользователя в функцию
@r.message(Command("recipes"))
@session_manager.connection(commit=True)
async def get_random_recipe(message: Message, session: AsyncSession):
    # вынести две строки ниже в Middleware, используется в get_random
    user_schema = GetUserDB(telegram_id=message.from_user.id)
    user: User = await UsersDAO.find_one_or_none(session, user_schema)
    recipes = await RecipesDAO.find_all(session, UserIDDB(user_id=user.id))

    if not recipes:
        await message.answer("У вас еще нет рецептов! Добавьте их с помощью команды /add_recipe")
        return

    await message.answer("Ваши рецепты:")

    for recipe in recipes:
        await message.answer(recipe)

