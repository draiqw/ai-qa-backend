from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

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

# Функция для получения сессии
async def get_db():
    async with SessionLocal() as session:
        yield session
