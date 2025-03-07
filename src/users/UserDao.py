# dao/user_dao.py
from typing import List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.dao.base import BaseDAO
from src.users.models import User

class UserDAO(BaseDAO[User]):
    model = User

    @classmethod  # Если нужны дополнительные опции загрузки
    async def get_all(cls, session: AsyncSession) -> List[User]:
        result = await session.execute(select(cls.model))
        return result.scalars().all()
