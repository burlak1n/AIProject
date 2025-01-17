from pydantic import BaseModel, EmailStr, Field


class GetUserDB(BaseModel):
    telegram_id: int = Field(description="TGID пользователя")

class AddUserDB(GetUserDB):
    username: str = Field(description="Username пользователя")
    fullname: str = Field(description="Полное имя пользователя")
    email: EmailStr = Field(description="Электронная почта")

class UserIDDB(BaseModel):
    id: int = Field(description="ID пользователя в БД")
