import uuid

from pydantic import Field

from app.schemas.base import ORMModel


class StudentCreate(ORMModel):
    roll_number: str
    name: str
    email: str
    branch: str
    phone: str
    linkedin_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    matchmaking_opt_in: bool = False


class StudentRead(StudentCreate):
    id: uuid.UUID
