from pydantic import BaseModel
from typing import Generic, List, TypeVar

T = TypeVar("T")

class PagePaginate(BaseModel, Generic[T]):
    values: List[T]
    total: int
    page: int
    pages: int
    page_size: int
