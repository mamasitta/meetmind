from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255))
    transcript: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="meeting")
    chunks: Mapped[list["MeetingChunk"]] = relationship(back_populates="meeting")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    owner: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[Optional[str]] = mapped_column(String(50))
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")


class MeetingChunk(Base):
    __tablename__ = "meeting_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column()
    # pgvector column — 1536 dimensions for text-embedding-3-small
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="chunks")