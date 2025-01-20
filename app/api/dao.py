from loguru import logger
from sqlalchemy import and_, select
from app.dao.base import BaseDAO
from app.api.models import User, Recipe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
class UsersDAO(BaseDAO):
    model = User

class RecipesDAO(BaseDAO):
    model = Recipe

    @classmethod
    async def find_from_non_privacy(cls, user_id: int, session: AsyncSession):
        # Найти запись по ID
        logger.info(f"Поиск чужих {cls.model.__name__}s; От ID: {user_id}")
        try:
            query = select(cls.model).filter(
                and_(
                    cls.model.user_id != user_id,
                    cls.model.user.privacy != True
                )
            )
            result = await session.execute(query)
            record = result.scalar_one_or_none()
            if record:
                logger.info(f"Запись с ID {user_id} найдена.")
            else:
                logger.info(f"Запись с ID {user_id} не найдена.")
            return record
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске записи с ID {user_id}: {e}")
            raise