from typing import List
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from .models import User

class MyBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class GetUserDB(MyBaseModel):
    telegram_id: int = Field(description="TGID пользователя")

class AddUserDB(GetUserDB):
    username: str = Field(description="Username пользователя")
    fullname: str = Field(description="Полное имя пользователя")
    email: EmailStr = Field(description="Электронная почта")

class UserIDDB(MyBaseModel):
    id: int = Field(description="ID пользователя в БД")

class GetRecipeDB(MyBaseModel):
    user_id: int = Field(description="ID пользователя")
    
class AddRecipeDB(GetRecipeDB):
    title: str = Field(description="Название рецепта")
    ingridiends: List[str] = Field(description="Шаги")
    steps: List[str] = Field(description="Шаги")
    model_config = ConfigDict(from_attributes=True)