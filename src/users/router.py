import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from jwt import PyJWTError
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

from src.dao.database import get_db
from src.users.models import User
from src.users.schemas import UserCreateSchema, UserResponseSchema
from src.users.UserDao import UserDAO

# Настройки безопасности
SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key_here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth")

router = APIRouter()

# Функция для создания JWT токена
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Регистрация пользователя
@router.post("/users")
async def register_user(
    user: UserCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    new_user = await UserDAO.register(
        session=db,
        user=user
    )
    return {
        "message": f"Пользователь успешно {new_user.login}"
                   f" зарегистрирован",
        "user_id": {new_user.id}
    }

# Получение списка пользователей
@router.get("/users", response_model=list[UserResponseSchema])
async def get_all_users(
        db: AsyncSession = Depends(get_db)
):
    page_result = await UserDAO.paginate(
        session=db,
        page=1,
        page_size=-1
    )
    return page_result.values

# Обновление данных пользователя
@router.put("/users/{user_id}", response_model=UserResponseSchema)
async def update_user(
        user_id: str,
        user_update: UserCreateSchema,
        db: AsyncSession = Depends(get_db)
):
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = UserDAO.pwd_context.hash(
            update_data["password"]
        )
    updated_user = await UserDAO.update(
        session=db,
        id=user_id,
        **update_data)
    return updated_user


# Удаление пользователя
@router.delete("/users/{user_id}")
async def delete_user(
        user_id: str,
        db: AsyncSession = Depends(get_db)
):
    deleted_user = await UserDAO.delete(
        session=db,
        id=user_id
    )
    return {
        "message": "Пользователь удалён",
        "deleted_id": str(deleted_user.id)
    }


# Аутентификация (получение токена)
@router.post("/auth", response_model=dict)
async def authenticate_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    user = (await UserDAO.paginate(
        email=form_data.username)
    ).values[0]

    if not user or not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# Получение текущего пользователя
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    user = await UserDAO.get(
        session=db,
        id=user_id
    )
    if user is None:
        raise credentials_exception
    return user

# Эндпоинт получения профиля текущего пользователя
@router.get("/profile", response_model=UserResponseSchema)
async def read_profile(
        current_user: User = Depends(get_current_user)
):
    return current_user


# Эндпоинт обновления профиля текущего пользователя
@router.put("/profile", response_model=UserResponseSchema)
async def update_profile(
        user_update: UserCreateSchema,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    update_data = user_update.dict(exclude_unset=True)

    if "password" in update_data:
        update_data["password"] = pwd_context.hash(update_data["password"])

    updated_user = await UserDAO.update(session=db, id=current_user.id, **update_data)
    return updated_user

