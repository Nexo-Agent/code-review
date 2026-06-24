from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExampleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ExampleResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
