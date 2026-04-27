import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


class OptionCreate(BaseModel):
    text: str
    is_correct: bool = False


class OptionResponse(BaseModel):
    id: uuid.UUID
    text: str
    is_correct: bool

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    text: str
    time_limit: int = 30
    options: list[OptionCreate]

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if len(v) != 4:
            raise ValueError("Each question must have exactly 4 options")
        correct_count = sum(1 for o in v if o.is_correct)
        if correct_count != 1:
            raise ValueError("Exactly one option must be marked as correct")
        return v


class QuestionUpdate(BaseModel):
    text: str | None = None
    time_limit: int | None = None
    options: list[OptionCreate] | None = None

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError("Each question must have exactly 4 options")
        correct_count = sum(1 for o in v if o.is_correct)
        if correct_count != 1:
            raise ValueError("Exactly one option must be marked as correct")
        return v


class QuestionResponse(BaseModel):
    id: uuid.UUID
    text: str
    time_limit: int
    creator_id: uuid.UUID
    created_at: datetime
    options: list[OptionResponse]

    model_config = {"from_attributes": True}