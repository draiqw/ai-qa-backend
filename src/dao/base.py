from typing import (
    Any, Dict, Generic, List, Optional, Type, TypeVar, Union, Unpack
)

from pydantic import BaseModel

from sqlalchemy import (
    Select,
    and_,
    delete as sqlalchemy_delete,
    func,
    insert,
    literal,
    or_,
    union_all,
    update as sqlalchemy_update,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.dao.schemas import PagePaginate
from src.dao.session_manager import SessionManager


ModelType = TypeVar("ModelType")
SchemaType = TypeVar("SchemaType", bound=BaseModel)


class BaseDAO(Generic[ModelType]):
    """Базовый класс для работы с БД"""

    model: Type[ModelType]
    options: List[Any] = []

    @classmethod
    def _get_entity_name(cls) -> str:
        """Получение имени сущности для сообщений об ошибках.

        Используется для более понятного вывода имени таблицы
        при возникновении ошибок.
        """
        return cls.model._tablename

    @classmethod
    @SessionManager.with_session()
    async def count_number(
        cls,
        session: AsyncSession,
        **filter_by: Unpack[Dict[str, Any]],
    ) -> Optional[ModelType]:
        """Подсчитывает количество записей в таблице, удовлетворяющих условиям.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            filter_by - именованные параметры для фильтрации записей.
        Возвращает:
            Количество записей, удовлетворяющих условию.
        """
        count_query = (
            select(func.count())
            .select_from(cls.model)
            .where(*[getattr(cls.model, k) == v for k, v in filter_by.items()])
        )

        result = await session.execute(count_query)
        return result.scalar()

    @classmethod
    @SessionManager.with_session()
    async def get(
        cls,
        session: AsyncSession,
        id: int,  # noqa
    ) -> Optional[ModelType]:
        """Получает запись по её первичному ключу.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            id - идентификатор записи.
        Возвращает:
            Запись, найденную по id. Если запись не найдена,
            выбрасывается исключение.
        """
        query = select(cls.model).filter_by(id=id).options(*cls.options)
        result = await session.execute(query)
        return result.scalar_one()

    @classmethod
    @SessionManager.with_session(auto_commit=True)
    async def create(
        cls,
        session: AsyncSession,
        returning: bool = True,
        **values: Unpack[Dict[str, Any]],
    ) -> Optional[ModelType]:
        """Создаёт новую запись в базе данных.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            returning - если True, метод возвращает созданный объект.
            values - значения для создания записи.
        Возвращает:
            Созданный объект или количество затронутых строк.
            Если запись не была создана, выбрасывается исключение.
        """
        query = insert(cls.model).values(**values)

        if returning:
            query = query.returning(cls.model).options(*cls.options)
        result = await session.execute(query)
        if returning:
            return result.scalar_one()

    @classmethod
    @SessionManager.with_session(auto_commit=True)
    async def create_many(
        cls,
        session: AsyncSession,
        values_list: List[Dict[str, Any]],
        returning: bool = True
    ) -> Optional[List[ModelType]]:
        """Массовое создание записей.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            values_list - список словарей с данными для создания записей.
            returning - если True, возвращает список созданных объектов.
        Возвращает:
            Список созданных объектов или количество созданных записей.
        """
        if not values_list:
            if returning:
                return []

        query = insert(cls.model)

        if returning:
            query = query.returning(cls.model).options(*cls.options)
        else:
            query = query.returning(cls.model.id)

        result = await session.execute(query, values_list)
        if returning:
            created_objs = result.scalars().all()
            if len(created_objs) != len(values_list):
                raise NoResultFound
            return created_objs
        if len(result.scalars().all()) != len(values_list):
            raise NoResultFound

    @classmethod
    @SessionManager.with_session(auto_commit=True)
    async def update(
        cls,
        session: AsyncSession,
        id: Union[int, str],  # noqa
        returning: bool = True,
        **values: Any,
    ) -> Optional[ModelType]:
        """Обновляет запись по её идентификатору.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            id - идентификатор записи.
            returning - если True, возвращает обновлённый объект.
            values - поля и их новые значения для обновления.
        Возвращает:
            Обновлённый объект или количество затронутых строк.
            Если запись не найдена, выбрасывается исключение.
        """
        query = (
            sqlalchemy_update(cls.model)
            .where(cls.model.id == id)
            .values(**values)
        )

        if returning:
            query = query.returning(cls.model).options(*cls.options)
        else:
            query = query.returning(cls.model.id)

        result = await session.execute(query)

        if returning:
            updated_obj = result.scalar_one()
            await session.refresh(updated_obj)
            return updated_obj

        result.scalar_one()

    @classmethod
    @SessionManager.with_session(auto_commit=True)
    async def update_many(
        cls,
        session: AsyncSession,
        values_list: List[Dict[str, Any]],
        returning: bool = True
    ) -> Optional[Union[int, List[ModelType]]]:
        """
        Массовое обновление записей с сохранением исходного порядка.

        Если returning=True, обновление происходит батчами
        (например, по 1000 записей),
        для каждого батча сразу производится SELECT обновлённых записей
        с сортировкой по порядковому номеру,
        определяемому исходным списком.
        Итоговый список – конкатенация результатов батчей.
        """
        if not values_list:
            if returning:
                return []
            else:
                return

        for value in values_list:
            if not value.get('id'):
                raise

        # Получаем все уникальные колонки для обновления из всех записей
        update_columns = set().union(
            *[item.keys() for item in values_list]
        ) - {'id'}

        # Формируем CTE для всех значений сразу
        values_query = (
            union_all(*[
                select(*[
                    literal(
                        item.get(col),
                        type_=cls.model.__table__.columns[col].type
                    ).label(col)
                    for col in ['id'] + list(update_columns)
                ])
                for item in values_list
            ])
            .cte('v')
        )

        # Выполняем обновление всех записей одним запросом
        update_query = (
            sqlalchemy_update(cls.model)
            .where(cls.model.id == values_query.c.id)
            .values({
                col: getattr(values_query.c, col)
                for col in update_columns
            })
        )

        if returning:
            update_query = (
                update_query
                .returning(cls.model)
                .options(*cls.options)
            )
        else:
            update_query = update_query.returning(cls.model.id)

        result = await session.execute(update_query)

        if returning:

            updated_objects = result.scalars().all()

            # Проверяем, что все записи были обновлены
            if len(updated_objects) != len(values_list):
                raise NoResultFound

            ids = [item["id"] for item in values_list]

            updated_dict = {obj.id: obj for obj in updated_objects}

            updated_objects = []
            for id_ in ids:
                obj = updated_dict.get(id_)
                if obj:
                    updated_objects.append(obj)

            id_positions = {id_val: index for index, id_val in enumerate(ids)}

            updated_objects = sorted(updated_objects,
                                     key=lambda obj: id_positions.get(obj.id))

            return updated_objects

        if len(result.scalars().all()) != len(values_list):
                raise NoResultFound

    @classmethod
    @SessionManager.with_session(auto_commit=True)
    async def delete(
        cls,
        session: AsyncSession,
        id: Union[int, str],  # noqa
        returning: bool = True,
    ) -> Optional[ModelType]:
        """Удаляет запись по её идентификатору.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            id - идентификатор записи для удаления.
            returning - если True, возвращает удалённый объект.
        Возвращает:
            Удалённый объект или количество затронутых строк.
            Если запись не найдена, выбрасывается исключение.
        """
        query = sqlalchemy_delete(cls.model).where(cls.model.id == id)
        if returning:
            query = query.returning(cls.model).options(*cls.options)
        else:
            query = query.returning(cls.model.id)
        result = await session.execute(query)
        if returning:
            deleted_obj = result.scalar_one()
            return deleted_obj

        result.scalar_one()

    @classmethod
    @SessionManager.with_session(auto_commit=True)
    async def delete_many(
        cls,
        session: AsyncSession,
        ids: List[Union[int, str]],
        returning: bool = True,
    ) -> Optional[List[ModelType]]:
        """Массовое удаление записей.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            ids - список идентификаторов записей для удаления.
            returning - если True, возвращает список удалённых объектов.
        Возвращает:
            Список удалённых объектов или количество удалённых записей.
            Если количество удалённых записей не совпадает с ожидаемым,
            выбрасывается исключение.
        """
        if not ids:
            if returning:
                return []
        query = sqlalchemy_delete(cls.model).where(cls.model.id.in_(ids))
        if returning:
            query = query.returning(cls.model).options(*cls.options)
        else:
            query = query.returning(cls.model.id)
        result = await session.execute(query)
        if returning:
            deleted_objs = result.scalars().all()
            if len(deleted_objs) != len(ids):
                raise NoResultFound
            return deleted_objs
        if len(result.scalars().all()) != len(ids):
            raise NoResultFound

    @classmethod
    @SessionManager.with_session(auto_commit=False)
    async def paginate(
        cls,
        session: AsyncSession,
        page: int = 1,
        page_size: int = -1,
        search_query: Optional[str] = None,
        base_query: Optional[Select] = None,
        search_fields: Optional[List[str]] = None,
        include_nullable: Optional[bool] = True,
        **filters: Unpack[Dict[str, Any]]
    ) -> PagePaginate:
        """Пагинация (разбиение на страницы) выборки записей.

        Параметры:
            session - асинхронная сессия SQLAlchemy.
            page - номер текущей страницы.
            page_size - количество записей на страницу
            (-1 означает, что пагинация не применяется).
            search_query - поисковый запрос для фильтрации по текстовым полям.
            base_query - базовый запрос для выборки
            (если не указан, используется запрос по модели).
            search_fields - список полей модели,
            по которым будет применяться поиск.
            filters - дополнительные условия фильтрации.
        Возвращает:
            Объект PagePaginate, содержащий список записей,
            общее количество записей,
            номер текущей страницы, общее количество страниц и размер страницы.
        """
        query = base_query if base_query is not None else select(cls.model)

        # Добавляем опции загрузки связанных данных
        query = query.options(*cls.options)

        # Добавляем условия поиска если есть поисковый запрос
        if search_query and search_fields:
            search_conditions = []
            query_text = f"%{search_query.strip().lower()}%"

            for field_name in search_fields:
                if hasattr(cls.model, field_name):
                    field = getattr(cls.model, field_name)
                    search_conditions.append(
                        func.lower(field).like(query_text)
                    )
            if search_conditions:
                query = query.where(or_(*search_conditions))

        # Добавляем дополнительные фильтры
        filter_conditions = []
        for field_name, value in filters.items():
            if hasattr(cls.model, field_name):
                field = getattr(cls.model, field_name)
                if value is None and include_nullable:
                    filter_conditions.append(field.is_(None))
                elif value is not None:
                    filter_conditions.append(field == value)
        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        # Получаем общее количество записей для пагинации
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)

        if page_size == -1:
            total_pages = 1
            page = 1
        else:
            total_pages = (total + page_size - 1) // page_size
            page = min(max(1, page), total_pages) if total_pages > 0 else 1
            query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        items = result.scalars().all()

        return PagePaginate(
            values=items,
            total=total,
            page=page,
            pages=total_pages,
            page_size=page_size
        )
