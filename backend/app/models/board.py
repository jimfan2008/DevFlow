#!/usr/bin/env python3
"""
DevFlow 看板模型
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class Board(Base):
    __tablename__ = "boards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    description = Column(Text)
    position = Column(Integer, default=0)
    color = Column(String(7), default="#3B82F6")
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="boards")
    columns = relationship("BoardColumn", back_populates="board", passive_deletes=True)

    __table_args__ = (
        Index("idx_boards_project", "project_id"),
        UniqueConstraint("project_id", "slug", name="uq_board_project_slug"),
    )


class BoardColumn(Base):
    __tablename__ = "board_columns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    color = Column(String(7), default="#E5E7EB")
    position = Column(Integer, default=0)
    max_tasks = Column(Integer)
    is_swimlane = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    board = relationship("Board", back_populates="columns")

    __table_args__ = (
        Index("idx_board_columns_board", "board_id"),
        UniqueConstraint("board_id", "slug", name="uq_board_column_board_slug"),
    )
