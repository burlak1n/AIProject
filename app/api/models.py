from app.dao.base import Base
from app.dao.database import uniq_str_an
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

class User(Base):
    """
    Модель таблицы пользователей, регистрирующихся при первом использовании бота.
    """
    telegram_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    username: Mapped[uniq_str_an]
    fullname: Mapped[uniq_str_an]
    email: Mapped[uniq_str_an]

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username}, fullname={self.fullname}, reg_time={self.created_at}, last_used={self.updated_at}>"
    
class Recipe(Base):
    title: Mapped[str]
    ingridiends: Mapped[Mapped[str]]
    steps: Mapped[Mapped[str]]

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User")

    # Будет вызываться при repr() | str() | print()
    def __repr__(self):
        text = f"<b>{self.title}</b>\n\nИнгредиенты:\n"
        for ingredient in self.ingridiends:
            text += f"- {ingredient}\n"
        
        text += "\nШаги приготовления:\n"
        for step in self.steps:
            text += f"{step}\n"
        
        return text
