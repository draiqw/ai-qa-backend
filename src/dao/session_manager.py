from functools import wraps
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.dao.database import async_session_maker
from src.dao.db_error_handler import DatabaseErrorHandler


class SessionManager:
    """Менеджер сессий для работы с БД"""

    @staticmethod
    def with_session(auto_commit: bool = False): # noqa
        def decorator(func): # noqa
            @wraps(func) # noqa
            async def wrapper(
                    cls: Any,
                    *args: Any,
                    session: AsyncSession = None,
                    **kwargs: Any
            ): # noqa
                try:
                    if session is not None:
                        result = await func(
                            cls, *args, session=session, **kwargs
                        )
                        return result

                    async with async_session_maker() as session:
                        if auto_commit:
                            async with session.begin():
                                result = await func(
                                    cls, *args, session=session, **kwargs
                                )
                                return result
                        else:
                            result = await func(
                                cls, *args, session=session, **kwargs
                            )
                            return result
                except Exception as e:
                    await session.rollback()
                    DatabaseErrorHandler.handle_error(e, cls)

            return wrapper

        return decorator
