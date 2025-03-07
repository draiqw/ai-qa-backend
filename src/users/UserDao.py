from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.dao.base import BaseDAO
from src.users.models import User

class UserDAO(BaseDAO[User]):
    model = User

    @classmethod
    async def get_all(cls, session: AsyncSession) -> List[User]:
        result = await session.execute(select(cls.model))
        return result.scalars().all()

    @classmethod
    async def get_by_unique_fields(cls, session: AsyncSession, **fields) -> Optional[User]:
        query = select(cls.model)
        for key, value in fields.items():
            query = query.where(getattr(cls.model, key) == value)
        result = await session.execute(query)
        return result.scalars().first()
