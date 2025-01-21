from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

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
