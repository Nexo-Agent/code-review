from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
