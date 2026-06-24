from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_conn
from app.repositories.examples import ExampleRepository, ExampleRow
from app.schemas.example import ExampleCreate, ExampleResponse

router = APIRouter()


def _to_response(row: ExampleRow) -> ExampleResponse:
    return ExampleResponse(id=row.id, name=row.name, created_at=row.created_at)


@router.get("", response_model=list[ExampleResponse])
async def list_examples(
    conn: asyncpg.Connection = Depends(get_conn),
) -> list[ExampleResponse]:
    repo = ExampleRepository(conn)
    rows = await repo.list()
    return [_to_response(row) for row in rows]


@router.post("", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    payload: ExampleCreate,
    conn: asyncpg.Connection = Depends(get_conn),
) -> ExampleResponse:
    repo = ExampleRepository(conn)
    row = await repo.create(payload.name)
    return _to_response(row)


@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(
    example_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> ExampleResponse:
    repo = ExampleRepository(conn)
    row = await repo.get(example_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _to_response(row)
