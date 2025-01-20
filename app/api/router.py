import random
from typing import List
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.api.dao import UsersDAO, RecipesDAO
from app.api.middleware import AuthMiddleware
from app.dao.session_maker import session_manager
from app.api.models import User, Recipe
from app.api.schemas import GetRecipeDB, GetUserDB, UserIDDB, AddRecipeDB
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from utils import find_similar_recipes, create_tfidf_vectors

r_user = Router()
r_user.message.middleware(AuthMiddleware())

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

# Команда /help
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

@r_user.message(Command("random_recipe"))
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
async def get_random_recipe(message: Message, session: AsyncSession, user: User):
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
    user.private = not user.private
    await session.commit()
    await message.answer(f"Ваша приватность изменена на {user.private}")

@r_user.message(Command("find"))
@session_manager.connection()
async def name_menu(message:Message, session: AsyncSession, user: User):
    recipes: List[Recipe] = await RecipesDAO.find_from_non_privacy(session, GetRecipeDB(user_id=user.id))
    tfidf_matrix, vectorizer = create_tfidf_vectors(recipes)

    msg = message.text.split(maxsplit=1)
    if len(msg) > 1:
        print(msg[1])
        for recipe in find_similar_recipes(msg[1], recipes, tfidf_matrix, vectorizer):
            await message.reply(str(recipe))
    else:
        await message.reply("Укажите ингредиент после команды /find.")