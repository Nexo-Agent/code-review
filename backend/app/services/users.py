from app.repositories.users import UserRepository
from app.schemas.user import UserListItemResponse, UserListResponse


async def list_users_paginated(
    conn,
    *,
    search: str | None,
    limit: int,
    offset: int,
) -> UserListResponse:
    repo = UserRepository(conn)
    query = (search or "").strip()
    rows = await repo.list_paginated(search=query, limit=limit, offset=offset)
    total = await repo.count(search=query)
    return UserListResponse(
        items=[
            UserListItemResponse(
                id=row.id,
                email=row.email,
                name=row.name,
                username=row.username,
                auth_source=row.auth_source,
                is_org_admin=row.is_org_admin,
                is_superuser=row.is_superuser,
                team_names=row.team_names,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
    )
