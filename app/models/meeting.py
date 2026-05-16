from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey, func, Table, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.core.database import Base

# Association table for many-to-many relationship between decisions and risks
# (if a risk can affect multiple decisions)
decision_risk_association = Table(
    "decision_risk_association",
    Base.metadata,
    mapped_column("decision_id", UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE")),
    mapped_column("risk_id", UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE")),
)

# Association table for action_items and risks
action_item_risk_association = Table(
    "action_item_risk_association",
    Base.metadata,
    mapped_column("action_item_id", UUID(as_uuid=True), ForeignKey("action_items.id", ondelete="CASCADE")),
    mapped_column("risk_id", UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE")),
)


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255))
    transcript: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Store extracted summary
    participants: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)  # Store participants list
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    chunks: Mapped[list["MeetingChunk"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    owner: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[Optional[str]] = mapped_column(String(50))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")
    risks: Mapped[list["Risk"]] = relationship(
        secondary=action_item_risk_association,
        back_populates="action_items"
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    made_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="decisions")
    risks: Mapped[list["Risk"]] = relationship(
        secondary=decision_risk_association,
        back_populates="decisions"
    )


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    related_to: Mapped[Optional[str]] = mapped_column(String(50))  # 'general', 'decision', 'action'
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="risks")
    decisions: Mapped[list["Decision"]] = relationship(
        secondary=decision_risk_association,
        back_populates="risks"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        secondary=action_item_risk_association,
        back_populates="risks"
    )


class MeetingChunk(Base):
    __tablename__ = "meeting_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column()
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="chunks")