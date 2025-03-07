import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from src.users.models import Base, User  # Импортируем базовые модели
from sqlalchemy import select

# Загружаем переменные окружения
load_dotenv()

# Получаем переменные для подключения к PostgreSQL
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")

# Формируем строку подключения
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

# Создаём асинхронный движок и сессию
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def update_migrations():
    """Применение миграций (если используем Alembic)"""
    os.system("alembic upgrade head")


async def fill_db():
    """Заполнение базы начальными данными"""
    async with SessionLocal() as session:
        async with session.begin():
            # Пример добавления тестового пользователя
            user = User(username="test_user", email="test@example.com", is_admin=False)
            session.add(user)
        await session.commit()
    print("База данных успешно заполнена начальными данными!")


async def create_admin():
    """Создание администратора, если его ещё нет"""
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.is_admin == True))
        admin_exists = result.scalars().first()

        if not admin_exists:
            async with session.begin():
                admin_user = User(username="admin", email="admin@example.com", is_admin=True)
                session.add(admin_user)
            await session.commit()
            print("Администратор успешно создан!")
        else:
            print("Администратор уже существует!")


async def clean():
    """Очистка базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("База данных очищена!")


async def main():
    """Обработка команд из аргументов"""
    import sys

    if len(sys.argv) < 2:
        print("Укажите команду: update_migrations | fill_db | create_admin | clean")
        return

    command = sys.argv[1]
    if command == "update_migrations":
        await update_migrations()
    elif command == "fill_db":
        await fill_db()
    elif command == "create_admin":
        await create_admin()
    elif command == "clean":
        await clean()
    else:
        print("Неизвестная команда")


if __name__ == "__main__":
    asyncio.run(main())
