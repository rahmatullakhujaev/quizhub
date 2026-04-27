import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class RoomStatus(str, enum.Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    host_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    collection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("collections.id"), nullable=True)
    status: Mapped[RoomStatus] = mapped_column(
    Enum(RoomStatus, values_callable=lambda x: [e.value for e in x]),
    default=RoomStatus.WAITING,
        )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    host: Mapped["User"] = relationship(back_populates="rooms")
    collection: Mapped["Collection"] = relationship()