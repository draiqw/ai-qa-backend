import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from src.ticket.models import Ticket
from src.dao.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp
from src.users.models import User
from sqlalchemy.future import select


router_tick = APIRouter()

WEBHOOK_URL = "https://b24-51p4iu.bitrix24.ru/rest/10"
roles_access = ["admin", "manager"]


@router_tick.get("/users_bitrix/{user_id}")
async def get_user_info(user_id: str):
    """
    Получает информацию о пользователе по его ID через метод user.get.
    Если пользователь не найден, выбрасывается исключение.
    """
    if not user_id:
        raise ValueError("Не передан user_id")
        
    url = f"{WEBHOOK_URL}/zjrofq3dxym52f3l/user.get.json"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {"filter": {"ID": str(user_id)}}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if not data.get("result") or len(data["result"]) == 0:
                    raise Exception(f"Пользователь с ID {user_id} не найден")
                return data["result"][0]
            else:
                error_text = await response.text()
                raise Exception(f"Ошибка запроса: {response.status}, {error_text}")


@router_tick.get("/usersfeqfdasdas")
async def get_recent_chats():
    """
    Получает список последних чатов и фильтрует их по условию:
    идентификатор начинается с "chat" и заголовок содержит слово "открыт".
    Возвращает множество chat_id.
    """
    url = f"{WEBHOOK_URL}/5oahsh99suuad2tt/im.recent.list.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                chat_ids = set()
                if data.get("result"):
                    for chat in data["result"]["items"]:
                        if (str(chat.get('id', '')).startswith("chat") and 
                            "открыт" in str(chat.get('title', '')).lower()):
                            chat_ids.add(chat['id'])
                    return chat_ids
                else:
                    raise Exception("Данные не найдены.")
            else:
                text = await response.text()
                raise Exception(f"Ошибка: {response.status} - {text}")

async def get_chat_messages(chat_id: str, user_id: str, limit: int = 100):
    """
    Получает сообщения чата через метод im.dialog.messages.get.
    Возвращает словарь с данными чата.
    """
    url = f"{WEBHOOK_URL}/ncdv8k6vku3la2sv/im.dialog.messages.get"
    params = {"DIALOG_ID": chat_id, "LIMIT": limit}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("result"):
                    messages = data["result"].get("messages", [])
                    if not messages:
                        return {
                            "chat_id": chat_id,
                            "ticket_id": data["result"].get("chat_id", chat_id),
                            "first_message_date": None,
                            "last_message_date": None,
                            "last_operator_id": None,
                            "messages": {},
                            "is_resolved": False
                        }
                    messages_sorted = sorted(messages, key=lambda msg: msg.get("date"))
                    first_message_date = messages_sorted[0].get("date")
                    last_message_date = messages_sorted[-1].get("date")
                    
                    # Преобразуем список пользователей в словарь для быстрого доступа
                    users_by_id = { str(user["id"]): user for user in data["result"]["users"] }
                    operator_ids = list({
                        msg["author_id"]
                        for msg in data["result"]["messages"]
                        if (msg.get("author_id") and 
                            int(msg["author_id"]) != 0 and 
                            users_by_id.get(str(msg["author_id"]), {}).get("name") != "Гость")
                    })
                    ticket_id = data["result"].get("chat_id", chat_id)
                    last_message_text = messages_sorted[-1].get("text", "").lower()
                    is_resolved = ("решен" in last_message_text) or ("закрыт" in last_message_text)
                    messages_dict = {msg.get("text", ""): msg.get("date") for msg in messages_sorted}
                    
                    return {
                        "chat_id": chat_id,
                        "ticket_id": ticket_id,
                        "first_message_date": first_message_date,
                        "last_message_date": last_message_date,
                        "operator_ids": operator_ids,
                        "messages": messages_dict,
                        "is_resolved": is_resolved,
                    }
                else:
                    raise Exception("Ошибка: данные не найдены")
            else:
                text = await response.text()
                raise Exception(f"Ошибка запроса: {response.status} - {text}")

@router_tick.get("/tickets/{chat_id}")
async def get_chat_messages_endpoint(
    chat_id: str,
    user_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    # Проверяем наличие пользователя в базе
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user_obj = result.scalars().first()
        if not user_obj:
            return JSONResponse(content={"error": f"Пользователь с ID {user_id} не найден"}, status_code=404)
        if user_obj.role not in roles_access:
            return JSONResponse(content={"error": "У вас нет доступа к этой функции"}, status_code=403)
        
        try:
            chat_data = await get_chat_messages(chat_id, user_id, limit)
            return JSONResponse(content=chat_data)
        except Exception as e:
            return JSONResponse(content={"error": f"Произошла ошибка: {e}"}, status_code=500)
    except  Exception as e:
        return JSONResponse(content={"error": f"Произошла ошибка: {e}"}, status_code=500)
    

@router_tick.put("/tickets")
async def save_ticket(user_id: str, db: AsyncSession = Depends(get_db)):
    # Проверяем пользователя в базе
    result = await db.execute(select(User).where(User.id == user_id))
    user_obj = result.scalars().first()
    if not user_obj:
        return JSONResponse(content={"error": f"Пользователь с ID {user_id} не найден"}, status_code=404)
    if user_obj.role not in roles_access:
        return JSONResponse(content={"error": "У вас нет доступа к этой функции"}, status_code=403)
    
    try:
        chat_ids = await get_recent_chats()  # Возвращает множество chat_id
        for chat in chat_ids:
            ticket_data = await get_chat_messages(chat, user_id, limit=100)
            # Обработка данных тикета (ticket_data — это словарь)
            operators_email = []

            # Получаем email операторов
            for operator_id in ticket_data.get("operator_ids", []):
                operator_info = await get_user_info(operator_id)
                operator_email = operator_info.get("EMAIL")
                operators_email.append(operator_email)
            

            for operator_email in operators_email:
                result = await db.execute(select(User).where(User.email == operator_email))

                db_operator = result.scalars().first()

                if not db_operator:
                    raise Exception(f"Пользователь с email {operator_email} не найден")
                
                status = "closed" if ticket_data.get("is_resolved") else "open"

                new_ticket = Ticket(
                    id=str(uuid.uuid4()),
                    user_id=db_operator.id,
                    chat_id=ticket_data.get("chat_id"),
                    connection_type="chat",
                    dialogue=ticket_data.get("messages"),
                    status=status,
                    time_open=ticket_data.get("first_message_date"),
                    time_close=ticket_data.get("last_message_date"),
                    category="chat"
                )

                # Берем тикеты из БД по email (все которые соответствуют) и проверяем
                # если такой тикет уже есть по Chat_id, если есть continut иначе добавляем
                db.add(new_ticket)
                await db.commit()
                await db.refresh(new_ticket)
        return JSONResponse(content={"message": "Тикеты успешно сохранены"})
    except Exception as e:
        return JSONResponse(content={"error": f"Произошла ошибка: {e}"}, status_code=500)
            
@router_tick.delete("/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
        ticket = result.scalars().first()
        if not ticket:
            return JSONResponse(content={"error": f"Тикет с ID {ticket_id} не найден"}, status_code=404)
        await db.delete(ticket)
        await db.flush()
        await db.commit()
        return JSONResponse(content={"message": f"Тикет с ID {ticket_id} успешно удалён"})
    except Exception as e:
        return JSONResponse(content={"error": f"Произошла ошибка: {e}"}, status_code=500)


@router_tick.get("/tickets")
async def get_all_tickets(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Ticket))
        tickets = result.scalars().all()

        def ticket_to_dict(ticket: Ticket) -> dict:
            return {
                "id": str(ticket.id),
                "user_id": str(ticket.user_id),
                "chat_id": ticket.chat_id,
                "connection_type": ticket.connection_type,
                "dialogue": ticket.dialogue,
                "status": ticket.status,
                "time_open": ticket.time_open if ticket.time_open else None,
                "time_close": ticket.time_close if ticket.time_close else None,
                "category": ticket.category,
            }

        tickets_list = [ticket_to_dict(ticket) for ticket in tickets]
        return JSONResponse(content={"tickets": tickets_list})
    except Exception as e:
        return JSONResponse(content={"error": f"Произошла ошибка: {e}"}, status_code=500)
