import io
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
import soundfile as sf
from speech_recognition import Recognizer, AudioFile

from app.create_bot import bot, dp
from app.keyboards.kb import main_kb
import app.api.utils as ut
from app.api.router import r as router_recipes

from app.config import GigaChatKey
from gigachat import GigaChat


# GigaChat api автоматическая транскрибация. Можно ли отправить голос?
# Улучшить связь между пользователем и рецептом (Блог и аавтор)
# Все рецепты, которые вы сохраните, могут быть использованы другими пользователями, как и вы сможете использовать их рецепты
# При добавлении рецепта: embeddings меняется
# Доступ к роутеру по админке

hello_message = "Привет! Я твой помощник в мире кулинарии.\n"
command_list_message = \
'''
Команды:
/start - Регистрация
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
# Инициализация бота
router_main = Router()

class Image(StatesGroup):
    image = State()

@router_main.message(Command("find"))
async def name_menu(message:Message):
    msg = message.text.split(maxsplit=1)
    if len(msg) > 1:
        print(msg[1])
        for recipe in ut.find_similar_recipes(msg[1], ut.recipes, ut.tfidf_matrix, ut.vectorizer):
            await message.reply(ut.format_recipe(recipe))
    else:
        await message.reply("Укажите ингредиент после команды /find.")
    

@router_main.message(Command("image"))
async def name_menu(message:Message, state: FSMContext):
    await state.set_state(Image.image)
    await message.reply("Введите сообщение, по которому Kandinsky сгенерирует фотографию")

# Команда /start
@router_main.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"{hello_message}", reply_markup=main_kb)

# Команда /help
@router_main.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(command_list_message)

# ТЕКСТ | Отправляется в диалог с GigaChat
@router_main.message(F.text)
async def handle_text(message: Message):
    if message.text.strip().lower().startswith('привет'):
        await message.answer(f"Приветствую тебя и желаю приятной готовки!")
    elif '713560' in message.text.strip().lower():
        recipe = ut.load_recipes(True)
        await message.answer(f"Ты ввёл секретный код! Держи рецепт в подарок {recipe[0]}")
    else:
        with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
            response = giga.chat(message.text)
            await message.answer(f"GigaChat: {response.choices[0].message.content}")
            print()

# ДОКУМЕНТ | Загрузка csv, json для добавления рецепта
@router_main.message(F.document)
async def handle_document(message: Message, bot: Bot):
    file_name = f"./docs/{message.document.file_name}"
    print(file_name)
    try:
        await bot.download(message.document, file_name)
        
        if file_name.endswith(('.csv', '.json')):
            async with aiofiles.open(file_name, mode='r', encoding='utf-8') as file:
                data = await file.read()

            if file_name.endswith('.csv'):
                reader = csv.DictReader(io.StringIO(data), fieldnames=['title', 'ingredients', 'steps'], delimiter=";")
                rows = list(reader)
                for row in rows:
                    row['ingredients'] = row['ingredients'].split()
                    row['steps'] = [row['steps']]
                    ut.save_recipe(row)
            elif file_name.endswith('.json'):
                recipes = json.loads(data)
                for recipe in recipes:
                    ut.save_recipe(recipe)
                    
            await message.answer("Файл загружен успешно!")
        else:
            await message.answer("Поддерживаются только файлы формата CSV и JSON.")
    except Exception as e:
        await message.answer(f"Произошла ошибка при загрузке файла: {e}")

# Транскрибация, отправлять в диалог с GigaChat
@router_main.message(F.voice)
async def handle_audio(message: Message):
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
        await message.reply(f"Текст аудиосообщения: {text}")
    except Exception as e:
        await message.reply(f"Произошла ошибка при обработке аудиосообщения: {e}")
    
    os.remove(f'{filename}.wav')

async def main():
    dp.include_routers(
        router_main,
        router_recipes
    )

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())