import uuid
from datetime import datetime
from pydantic import BaseModel
from app.schemas.question import QuestionResponse


class CollectionCreate(BaseModel):
    title: str
    question_ids: list[uuid.UUID]


class CollectionUpdate(BaseModel):
    title: str | None = None
    question_ids: list[uuid.UUID] | None = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    title: str
    creator_id: uuid.UUID
    created_at: datetime
    questions: list[QuestionResponse]

    model_config = {"from_attributes": True}


class CollectionListResponse(BaseModel):
    id: uuid.UUID
    title: str
    creator_id: uuid.UUID
    created_at: datetime
    question_count: int

    model_config = {"from_attributes": True}