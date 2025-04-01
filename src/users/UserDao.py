import uuid
import os
import jwt
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.dao.base import BaseDAO
from src.users.models import User
from src.users.schemas import UserCreateSchema  # если имеется
from passlib.context import CryptContext # или откуда импортируется pwd_context
from datetime import datetime, timedelta


class UserDAO(BaseDAO[User]):
    model = User

    @classmethod
    async def register(cls, session: AsyncSession, user: UserCreateSchema) -> User:
        # Проверка уникальности пользователя через пагинацию
        page_result = await cls.paginate(
            session=session,
            page=1,
            page_size=1,
            email=user.email,
            phone=user.phone,
            login=user.login
        )
        if page_result.total > 0:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с такими данными уже существует"
            )
        # Подготовка данных: преобразование в dict, генерация id и хэширование пароля
        pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto"
        )

        user_data = user.dict(
            exclude_unset=True
        )
        user_data["id"] = uuid.uuid4()
        user_data["password"] = pwd_context.hash(
            user.password
        )

        new_user = await cls.create(
            session=session,
            **user_data
        )

        return new_user

