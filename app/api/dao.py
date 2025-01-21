from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import and_, select
from app.dao.base import BaseDAO
from app.api.models import User, Recipe
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
class UsersDAO(BaseDAO):
    model = User

    @classmethod
    async def find_all_to_schedule(cls, session: AsyncSession):
        logger.info(f"Поиск всех {cls.model.__name__}s, которым нужно прислать рассылку")
        try:
            now = datetime.now()
            query = select(cls.model).filter(now-cls.model.updated_at > timedelta(days=1))
            result = await session.execute(query)
            records = result.scalars().all()
            return records
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске всех {cls.model.__name__}s, которым нужно прислать рассылку: {e}")
            raise

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
            records = result.scalars().all()
            logger.info(f"Найдено {len(records)} записей.")

            return records
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске чужих рецептов от ID {user_id}: {e}")
            raise