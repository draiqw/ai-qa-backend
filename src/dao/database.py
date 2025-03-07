from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from src.dao.database import SessionLocal  
# Загружаем переменные окружения
load_dotenv()

# Получаем переменные для подключения к PostgreSQL
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")  # Имя сервиса PostgreSQL в Docker Composer

# Формируем строку подключения
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

# Создаём асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Создаём фабрику сессий
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Обеспечиваем доступ к фабрике сессий под нужным именем
async_session_maker = SessionLocal

# Базовый класс для моделей
Base = declarative_base()

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.dao.database import SessionLocal  # ваша фабрика сессий

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()  # автоматический commit после успешного запроса
        except Exception:
            await session.rollback()
            raise