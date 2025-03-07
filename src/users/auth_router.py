from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import sha256_crypt
import jwt
from jwt import PyJWTError

from .models import User
from .schemas import UserCreateSchema  # Можно переиспользовать эту схему для обновления профиля
from src.dao.database import get_db

# Настройки безопасности (при желании можно вынести в конфигурацию)
SECRET_KEY = "your_secret_key_here"  # Рекомендуется брать из переменных окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 схема для извлечения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Зависимость, которая извлекает пользователя на основании JWT-токена.
    Декодирует токен, проверяет срок действия и ищет пользователя в БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

router = APIRouter()

@router.get("/profile")
async def read_profile(current_user: User = Depends(get_current_user)):
    """
    Эндпоинт для получения данных личного кабинета текущего пользователя.
    """
    user_data = {
        "id": str(current_user.id),
        "name": current_user.name,
        "surname": current_user.surname,
        "middlename": current_user.middlename,
        "phone": current_user.phone,
        "login": current_user.login,
        "email": current_user.email,
        "role": current_user.role,
        "bitrix_id": current_user.bitrix_id
    }
    return user_data

@router.put("/profile")
async def update_profile(
    user_update: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Эндпоинт для обновления данных личного кабинета текущего пользователя.
    Обновляются только переданные поля.
    """
    if user_update.name is not None:
        current_user.name = user_update.name
    if user_update.surname is not None:
        current_user.surname = user_update.surname
    if user_update.middlename is not None:
        current_user.middlename = user_update.middlename
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.login is not None:
        current_user.login = user_update.login
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.password is not None:
        current_user.password = sha256_crypt.hash(user_update.password)
    if user_update.role is not None:
        current_user.role = user_update.role

    await db.commit()
    await db.refresh(current_user)
    return {"message": "Profile updated successfully"}
