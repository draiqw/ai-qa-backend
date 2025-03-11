import json
import uuid
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import sha256_crypt
import jwt
from jwt import PyJWTError
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta

from src.dao.database import get_db
from src.users.UserDao import UserDAO
from src.users.models import User
from src.users.schemas import UserCreateSchema, AuthSchema

router = APIRouter()

# Настройки безопасности (рекомендуется брать SECRET_KEY из переменных окружения)
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/users")
async def register_user(user: UserCreateSchema, db: AsyncSession = Depends(get_db)):
    # Проверка на существование пользователя по email, phone или login
    existing = await UserDAO.get_by_unique_fields(
        session=db,
        email=user.email,
        phone=user.phone,
        login=user.login
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Формируем данные для создания нового пользователя
    user_data = user.dict(exclude_unset=True)
    user_data["id"] = str(uuid4())
    user_data["password"] = sha256_crypt.hash(user.password)
    user_data["bitrix_id"] = None

    new_user = await UserDAO.create(session=db, **user_data)
    await db.commit()
    return {"message": f"You registered successfully: {new_user.login}"}

@router.get("/users")
async def get_all_users(db: AsyncSession = Depends(get_db)):
    users = await UserDAO.get_all(session=db)
    users_list = [
        {
            "id": str(user.id),
            "name": user.name,
            "surname": user.surname,
            "middlename": user.middlename,
            "phone": user.phone,
            "login": user.login,
            "email": user.email,
            "role": user.role,
            "bitrix_id": user.bitrix_id,
        }
        for user in users
    ]
    return {"users": users_list}

@router.get("/users/{user_id}")
async def get_user_by_id(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await UserDAO.get(session=db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = {
        "id": str(user.id),
        "name": user.name,
        "surname": user.surname,
        "middlename": user.middlename,
        "phone": user.phone,
        "login": user.login,
        "email": user.email,
        "role": user.role,
        "bitrix_id": user.bitrix_id,
    }
    return {"user": user_data}

@router.put("/users/{user_id}")
async def update_user(user_id: str, user_update: UserCreateSchema, db: AsyncSession = Depends(get_db)):
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = sha256_crypt.hash(update_data["password"])
    updated_user = await UserDAO.update(session=db, id=user_id, **update_data)
    await db.commit()
    return {"message": "User updated", "user": {
        "id": str(updated_user.id),
        "name": updated_user.name,
        "surname": updated_user.surname,
        "middlename": updated_user.middlename,
        "phone": updated_user.phone,
        "login": updated_user.login,
        "email": updated_user.email,
        "role": updated_user.role,
        "bitrix_id": updated_user.bitrix_id,
    }}

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    # FastAPI автоматически преобразует строку в UUID или выдаст ошибку 422, если формат неверный
    deleted_user = await UserDAO.delete(session=db, id=user_id)
    await db.commit()
    return {"message": "User deleted", "deleted_id": str(deleted_user.id)}

# Аутентификация и работа с профилем
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth")

@router.post("/auth")
async def authenticate_user(auth_data: AuthSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == auth_data.email))
    user = result.scalars().first()
    if not user or not sha256_crypt.verify(auth_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "message": f"User {user.login} authenticated successfully"
    }

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
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
    user = await UserDAO.get(session=db, id=user_id)
    if user is None:
        raise credentials_exception
    return user

@router.get("/profile")
async def read_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "surname": current_user.surname,
        "middlename": current_user.middlename,
        "phone": current_user.phone,
        "login": current_user.login,
        "email": current_user.email,
        "role": current_user.role,
        "bitrix_id": current_user.bitrix_id,
    }

@router.put("/profile")
async def update_profile(
    user_update: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    update_data = user_update.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = sha256_crypt.hash(update_data["password"])
    updated_user = await UserDAO.update(session=db, id=current_user.id, **update_data)
    return {"message": "Profile updated successfully", "user": {
        "id": str(updated_user.id),
        "name": updated_user.name,
        "surname": updated_user.surname,
        "middlename": updated_user.middlename,
        "phone": updated_user.phone,
        "login": updated_user.login,
        "email": updated_user.email,
        "role": updated_user.role,
        "bitrix_id": updated_user.bitrix_id,
    }}
