import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    time_limit: Mapped[int] = mapped_column(default=30)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator: Mapped["User"] = relationship(back_populates="questions")
    options: Mapped[list["Option"]] = relationship(back_populates="question", cascade="all, delete-orphan")

    # many-to-many with collections
    collections: Mapped[list["Collection"]] = relationship(
        secondary="collection_questions", back_populates="questions"
    )