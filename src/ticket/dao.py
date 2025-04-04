# файл: src/dao/dao.py

import uuid
import aiohttp
from typing import List
from sqlalchemy import Sequence
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from src.users.models import User
from src.ticket.models import Ticket
from src.dao.base import BaseDAO

class TicketDAO(BaseDAO[Ticket]):
    model = Ticket
    WEBHOOK_URL = "https://b24-ro4m0k.bitrix24.ru/rest/1"
    roles_access = ["admin", "manager"]
    @classmethod
    async def get_user_info(cls, bitrix_user_id: Optional[int] = None, email: Optional[str] = None) -> dict:
        """
        Получает информацию о пользователе по его Bitrix ID или email через метод user.get (из Bitrix24).
        Обязательно должен быть передан хотя бы один из параметров.
        """
        if not bitrix_user_id and not email:
            raise ValueError("Необходимо передать хотя бы один параметр: bitrix_user_id или email")

        url = f"{cls.WEBHOOK_URL}/7c2l2pndd6rmc44g/user.get.json"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Формируем фильтр: добавляем ключи, если соответствующие значения переданы
        filter_params = {}
        if bitrix_user_id:
            filter_params["ID"] = str(bitrix_user_id)
        if email:
            filter_params["EMAIL"] = email

        payload = {"filter": filter_params}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data.get("result") or len(data["result"]) == 0:
                        raise Exception(f"Пользователь с параметрами {payload['filter']} не найден в Bitrix24")
                    return data["result"][0]
                else:
                    error_text = await response.text()
                    raise Exception(f"Ошибка запроса: {response.status}, {error_text}")

    @classmethod
    async def get_recent_chats(cls) -> set:
        """
        Возвращает множество chat_id, у которых идентификатор начинается с "chat"
        и заголовок содержит слово "открыт" (через Bitrix24).
        """
        url = f"{cls.WEBHOOK_URL}/fx3u6sfrdgcemvn0/im.recent.list.json"
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

    @classmethod
    async def get_chat_messages(cls, chat_id: str, limit: int = 100) -> dict:
        """
        Получает сообщения чата (через Bitrix24), возвращает структуру данных о чате.
        """
        url = f"{cls.WEBHOOK_URL}/vxokddeh6q71x9gi/im.dialog.messages.get"
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
                                "operator_ids": [],
                                "messages": {},
                                "is_resolved": False
                            }

                        messages_sorted = sorted(messages, key=lambda msg: msg.get("date"))
                        first_message_date = messages_sorted[0].get("date")
                        last_message_date = messages_sorted[-1].get("date")

                        # Преобразуем список пользователей в словарь для быстрого доступа
                        users_by_id = {
                            str(user["id"]): user
                            for user in data["result"]["users"]
                        }

                        # Определяем идентификаторы операторов (не гости и не id=0)
                        operator_ids = list({
                            msg["author_id"]
                            for msg in data["result"]["messages"]
                            if ( msg.get("author_id")
                                 and int(msg["author_id"]) != 0
                                 and users_by_id.get(str(msg["author_id"]), {}).get("name") != "Гость")
                        })

                        ticket_id = data["result"].get("chat_id", chat_id)
                        last_message_text = messages_sorted[-1].get("text", "").lower()
                        is_resolved = ("решен" in last_message_text) or ("закрыт" in last_message_text)
                        messages_dict = {
                            msg.get("text", ""): msg.get("date") for msg in messages_sorted
                        }

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
                        raise Exception("Ошибка: данные не найдены в ответе Bitrix")
                else:
                    text = await response.text()
                    raise Exception(f"Ошибка запроса: {response.status} - {text}")

    @classmethod
    async def get_chat_messages_with_role_check(
        cls,
        chat_id: str,
        user_id: uuid.UUID,       # По факту у вас UUID (строка в URL), но хранится в БД как UUID
        limit: int,
        db: AsyncSession
    ) -> dict:
        """
        Проверяет наличие пользователя в локальной БД и его роль.
        Если роль допустимая, запрашивает сообщения чата через Bitrix24.
        """
        # Проверяем наличие пользователя в базе данных
        result = await db.execute(select(User).where(user_id == User.id))
        user_obj = result.scalars().first()
        if not user_obj:
            raise Exception(f"Пользователь с ID {user_id} не найден в локальной БД")

        if user_obj.role not in cls.roles_access:
            raise Exception("У вас нет доступа к этой функции (role check failed)")
        # Если всё хорошо — запрашиваем сообщения из Bitrix
        chat_data = await cls.get_chat_messages(chat_id, limit)
        return chat_data

    @classmethod
    async def get_all(cls, db: AsyncSession) -> List[Ticket]:
        """
        Получает все тикеты из базы данных.
        """
        result = await db.execute(select(Ticket))
        tickets = result.scalars().all()
        return tickets

    @classmethod
    async def  responsible_operators(cls,chat_id:str):
        endpoint = f"{cls.WEBHOOK_URL}/ixlly9svv3uw9my2/imopenlines.dialog.get.json"
        params = {"DIALOG_ID": chat_id}
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data:
                        result = data["result"]
                        return result.get("manager_list", [])
                    else:
                        raise Exception(f"Ошибка в ответе API: {data}")
                else:
                    text = await response.text()
                    raise Exception(f"Ошибка запроса: {response.status} - {text}")
