import json
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Redis для кэширования векторов всех рецептов?

def save_recipe(recipe):
    filename = 'recipes.json'
    
    # Проверяем, существует ли файл
    if not os.path.exists(filename):
        # Если файла нет, создаем его с начальной структурой []
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    # Теперь открываем файл в режиме "r+"
    with open(filename, 'r+', encoding='utf-8') as outfile:
        try:
            # Читаем содержимое файла
            outfile.seek(0)
            data = json.load(outfile)
            
            # Добавляем новый рецепт к существующему списку рецептов
            data.append(recipe)
        except json.JSONDecodeError:
            # Если файл был пустым, создаем список с одним рецептом
            data = [recipe]
        
        # Переводим курсор в начало файла и записываем обновленные данные
        outfile.seek(0)
        json.dump(data, outfile, indent=4, ensure_ascii=False)
        outfile.truncate()  # Убираем все лишнее после новой записи

def load_recipes(secret: bool = False):
    if secret:
        with open('secret.json', 'r', encoding='utf-8') as infile:
            return json.load(infile)
    try:
        with open('recipes.json', 'r', encoding='utf-8') as infile:
            return json.load(infile)
    except FileNotFoundError:
        return []

# Функция для загрузки рецептов из JSON файла
def load_recipes_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    return recipes

# Функция для создания TF-IDF матриц
def create_tfidf_vectors(recipes):
    # Объединяем ингредиенты и шаги каждого рецепта в одну строку
    descriptions = []
    for recipe in recipes:
        description = ', '.join(recipe['ingredients']) + ' | ' + ' '.join(recipe['steps'])
        descriptions.append(description)
    
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(descriptions)
    return tfidf_matrix, tfidf_vectorizer

# Функция для поиска похожих рецептов
def find_similar_recipes(query, recipes, tfidf_matrix, vectorizer):
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

recipes = load_recipes_from_json('db.json')
tfidf_matrix, vectorizer = create_tfidf_vectors(recipes)