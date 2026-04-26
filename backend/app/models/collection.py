import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Table, Column, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# association table for many-to-many
collection_questions = Table(
    "collection_questions",
    Base.metadata,
    Column("collection_id", UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
    Column("question_id", UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator: Mapped["User"] = relationship(back_populates="collections")
    questions: Mapped[list["Question"]] = relationship(
        secondary=collection_questions, back_populates="collections"
    )