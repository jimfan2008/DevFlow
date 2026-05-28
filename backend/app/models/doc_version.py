from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class DocVersion(Base):
    __tablename__ = "doc_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type = Column(String(50), nullable=False)
    version = Column(String(20), nullable=False)
    content_hash = Column(String(64), nullable=False)
    is_consistent = Column(Boolean, nullable=False, default=True)
    last_modified_by = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("Project", foreign_keys=[project_id])
    last_modifier = relationship("Agent", foreign_keys=[last_modified_by])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "doc_type": self.doc_type,
            "version": self.version,
            "content_hash": self.content_hash,
            "is_consistent": self.is_consistent,
            "last_modified_by": self.last_modified_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }