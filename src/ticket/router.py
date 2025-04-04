# файл: src/routers/tickets.py
from typing import Optional
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.ticket.models import Ticket
from src.ticket.schemas import TicketSchema

from src.dao.database import get_db
from src.ticket.dao import TicketDAO  # <-- импортируем наш класс DAO
from src.users.UserDao import UserDAO
from src.users.models import User
router_tick = APIRouter()

@router_tick.get("/users_bitrix")
async def get_user_info_endpoint(bitrix_user_id: Optional[int]=None,email: Optional[str] = None):
    """
    Получает информацию о пользователе по его ID через метод user.get (Bitrix24).
    Если пользователь не найден, выбрасывается исключение.
    """
    try:
        if email:
            user_info = await TicketDAO.get_user_info(email=email)
        elif bitrix_user_id:
            user_info = await TicketDAO.get_user_info(bitrix_user_id=bitrix_user_id)
        return JSONResponse(content=user_info)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

@router_tick.get("/bitrix")
async def get_recent_chats_endpoint():
    try:
        chat_ids = await TicketDAO.get_recent_chats()
        return JSONResponse(content=list(chat_ids))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

@router_tick.get("/tickets/{chat_id}")
async def create_chat_messages_bitrix(
    chat_id: str,
    user_id: uuid.UUID, #эта штука нужна чтобы понять кто заходит на сайт есть ли у него доступ
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Проверяет, что в локальной БД существует пользователь с данным user_id и
    что его роль позволяет просматривать чаты. Если всё нормально,
    запрашивает данные о сообщениях чата (через Bitrix24).
    """
    try:
        chat_data = await TicketDAO.get_chat_messages_with_role_check(
            chat_id=chat_id,
            user_id=user_id,
            limit=limit,
            db=db
        )
        allowed_keys = {"chat_id", "messages"}
        filtered_data = {key: value for key, value in chat_data.items() if key in allowed_keys}
        if "messages" in filtered_data:
            filtered_data["dialogue"] = filtered_data.pop("messages")
        filtered_data.setdefault("connection_type", "chat")
        filtered_data.setdefault("category", "default")  # или другое значение
        filtered_data.setdefault("user_id", None)
        operator_ids = await TicketDAO.responsible_operators(chat_id=chat_id)
        if not operator_ids:
            raise Exception("Ответственные операторы не найдены")

        for operator in operator_ids:
            user_info = await TicketDAO.get_user_info(bitrix_user_id=operator)
            email = user_info["EMAIL"]  # извлекаем строку email
            user_db = (await UserDAO.paginate(session=db, email=email)).values[0]
            filtered_data["user_id"]=user_db.id
            await TicketDAO.create(
                session=db,
                returning=False,
                **filtered_data
            )

        return JSONResponse(content=chat_data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)},status_code=400)


@router_tick.get("/tickets")
async def get_all_tickets(db: AsyncSession = Depends(get_db)):
    return await TicketDAO.get_all(db=db)

