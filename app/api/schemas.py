from typing import List
from pydantic import BaseModel, ConfigDict, Field

class MyBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class GetUserDB(MyBaseModel):
    telegram_id: int = Field(description="TGID пользователя")

class AddUserDB(GetUserDB):
    username: str = Field(description="Username пользователя")
    name: str = Field(description="Имя пользователя")
    fullname: str = Field(description="Полное имя пользователя")

class UserIDDB(MyBaseModel):
    id: int = Field(description="ID пользователя в БД")

class GetRecipeDB(MyBaseModel):
    user_id: int = Field(description="ID пользователя")

class AddRecipeDB(GetRecipeDB):
    title: str = Field(description="Название рецепта")
    ingridiends: List[str] = Field(description="Ингредиенты")
    steps: List[str] = Field(description="Шаги")
    model_config = ConfigDict(from_attributes=True)

class UpdateUserContraDB(BaseModel):
    telegram_id: int
    contra: str