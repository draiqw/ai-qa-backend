from typing import Any, Optional

from fastapi import HTTPException, status

from sqlalchemy.exc import IntegrityError, NoResultFound


class DatabaseErrorHandler:
    """Обработчик ошибок базы данных"""

    @staticmethod
    def parse_tablename(error_detail: str) -> Optional[str]:
        """Безопасный парсинг имени таблицы из сообщения об ошибке"""
        try:
            tablename_start = error_detail.find('in table "')
            if tablename_start == -1:
                return None
            tablename_start += 10
            tablename_end = error_detail.find('"', tablename_start)
            if tablename_end == -1:
                return None
            return error_detail[tablename_start:tablename_end]
        except Exception:
            return None

    @staticmethod
    def handle_integrity_error(error: IntegrityError, cls: Any) -> None:
        """Обработка ошибок целостности базы данных"""
        error_detail = str(error.orig)


        # Проверяем ошибки внешнего ключа
        error_detail_lower = error_detail.lower()
        if "violates foreign key constraint" in error_detail_lower:
            table_name = DatabaseErrorHandler.parse_tablename(error_detail)
            if table_name:
                for table in cls.model.__base__.__subclasses__():
                    if (hasattr(table, '__tablename__') and
                            table.__tablename__ == table_name):
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{table._tablename} не существует",
                        )

    @staticmethod
    def handle_error(error: Exception, cls: Any) -> None:
        """Общий обработчик ошибок"""
        if isinstance(error, HTTPException):
            raise error
        elif isinstance(error, NoResultFound):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{cls.model._tablename} не существует",
            )
        elif isinstance(error, IntegrityError):
            DatabaseErrorHandler.handle_integrity_error(error, cls)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обработке запроса",
        )
