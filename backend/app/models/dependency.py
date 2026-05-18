from sqlalchemy import Column, String, ForeignKey, DateTime, Index, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.database import Base


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    target_task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    source_task = relationship("Task", foreign_keys=[source_task_id], back_populates="source_dependencies")
    target_task = relationship("Task", foreign_keys=[target_task_id], back_populates="target_dependencies")

    __table_args__ = (
        Index("idx_task_deps_source", "source_task_id"),
        Index("idx_task_deps_target", "target_task_id"),
        CheckConstraint("source_task_id != target_task_id", name="ck_task_deps_no_self"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
