import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.room import RoomStatus
from app.schemas.collection import CollectionResponse


class RoomCreate(BaseModel):
    collection_id: uuid.UUID
    save_as_collection: bool = False
    collection_title: str | None = None
    question_ids: list[uuid.UUID] | None = None


class RoomResponse(BaseModel):
    id: uuid.UUID
    room_code: str
    host_id: uuid.UUID
    collection_id: uuid.UUID | None
    status: RoomStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class RoomDetailResponse(BaseModel):
    id: uuid.UUID
    room_code: str
    host_id: uuid.UUID
    status: RoomStatus
    created_at: datetime
    collection: CollectionResponse | None

    model_config = {"from_attributes": True}


class RoomJoinResponse(BaseModel):
    room_id: uuid.UUID
    room_code: str
    status: RoomStatus
    host_id: uuid.UUID