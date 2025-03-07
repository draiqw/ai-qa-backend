from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.dao.database import Base, engine
from src.users.router import router as user_router
from src.users.auth_router import router as auth_router
from src.ticket.router import router_tick as ticket_router

app = FastAPI()

# Настройка CORS: разрешаем запросы с указанных источников (например, с фронтенда на http://localhost:3000)
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8080",
    # Добавьте дополнительные источники по необходимости
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Разрешённые источники запросов
    allow_credentials=True,
    allow_methods=["*"],         # Разрешаем все методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],         # Разрешаем все заголовки
)

# Подключение маршрутов
app.include_router(user_router, prefix="/api", tags=["user"])
app.include_router(ticket_router, prefix="/api", tags=["ticket"])
app.include_router(auth_router, prefix="/api", tags=["auth"])

# Функция для создания таблиц в базе (используется при старте приложения)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("startup")
async def on_startup():
    await create_tables()

@app.get("/")
async def read_root():
    return {"message": "Welcome to the AI QA Backend"}
