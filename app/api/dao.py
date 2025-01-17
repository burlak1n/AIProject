from app.dao.base import BaseDAO
from app.api.models import User, Recipe

class UsersDAO(BaseDAO):
    model = User

class RecipesDAO(BaseDAO):
    model = Recipe