import asyncio
import os
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Загружаем конфигурацию Alembic
config = context.config
fileConfig(config.config_file_name)

# Импорт моделей (убедитесь, что Base содержит все модели, например User и Ticket)
from src.dao.database import Base

# Получаем URL базы данных из переменных окружения или используем значение по умолчанию для PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db/postgres")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Создаём асинхронный движок для PostgreSQL
engine = create_async_engine(DATABASE_URL, future=True, echo=True)

def run_migrations_offline():
    """Запуск миграций в offline-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
