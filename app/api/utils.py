import base64
from typing import List

from gigachat import GigaChat
from app.config import MAX_MESSAGE_LENGTH, GigaChatKey
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import io
import asyncio
from gigachat.models import Messages, MessagesRole, Chat

from app.api.models import Recipe

# Redis для кэширования векторов всех рецептов?

# Функция для создания TF-IDF матриц
async def create_tfidf_vectors(recipes: List[Recipe]):
    # Объединяем ингредиенты и шаги каждого рецепта в одну строку
    descriptions = []
    for recipe in recipes:
        description = ', '.join(recipe.ingridiends) + ' | ' + ' '.join(recipe.steps)
        descriptions.append(description)
    
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(descriptions)
    return tfidf_matrix, tfidf_vectorizer

# Функция для поиска похожих рецептов
async def find_similar_recipes(query, recipes, tfidf_matrix, vectorizer):
    # Обработка пустого запроса
    if not query:
        return []  # Возвращаем пустой список если запрос пустой
    
    # Преобразование запроса в вектор TF-IDF
    query_vec = vectorizer.transform([query])
    
    # Вычисление косинусного сходства
    similarity_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    
    # Сортировка индексов по убыванию сходства
    indices = np.argsort(similarity_scores)[::-1][:3]
    
    # Выбор трех самых похожих рецептов
    similar_recipes = [recipes[i] for i in indices]
    
    return similar_recipes

def truncate_message(text: str) -> str:
    if len(text) > MAX_MESSAGE_LENGTH:
        return text[:MAX_MESSAGE_LENGTH - 3] + "..."
    return text

# -------------------- Преобразование изображения в base64 --------------------
def image_bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")

async def text_to_speech(text: str, lang: str = 'ru') -> tuple[io.BytesIO, int]:
    """
    Преобразует текст в голосовое сообщение
    :param text: Текст для синтеза
    :param lang: Язык синтеза (по умолчанию 'ru')
    :return: Кортеж (BytesIO объект с аудио, длительность в секундах)
    """
    max_retries = 3
    retry_delay = 1  # начальная задержка в секундах
    
    for attempt in range(max_retries):
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            import io

            # Создаем MP3 с помощью gTTS
            tts = gTTS(text=text, lang=lang)
            
            # Сохраняем аудио в BytesIO
            mp3_buffer = io.BytesIO()
            tts.write_to_fp(mp3_buffer)
            mp3_buffer.seek(0)
            
            audio = AudioSegment.from_mp3(mp3_buffer)
            
            # Конвертируем в OGG
            ogg_buffer = io.BytesIO()
            audio.export(ogg_buffer, format="ogg")
            ogg_buffer.seek(0)
            
            # Получаем длительность аудио
            duration_seconds = int(len(audio) / 1000)
            
            return ogg_buffer, duration_seconds
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Ошибка при синтезе речи после {max_retries} попыток: {e}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Увеличиваем задержку экспоненциально

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


async def generate_text(text, payload=None):
    # Отправляем запрос к GigaChat
    with GigaChat(credentials=GigaChatKey, verify_ssl_certs=False) as giga:
        if not payload:
            payload = await init_giga_chat()
        payload.messages.append(Messages(role=MessagesRole.USER, content=text))
        response = giga.chat(payload)
        payload.messages.append(response.choices[0].message)
        return f"{response.choices[0].message.content}", payload
