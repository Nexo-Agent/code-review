from fastapi import Query

from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
        offset: int = Query(0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset
