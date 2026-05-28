from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base
from app.models.types import JSONB


class SecurityAudit(Base):
    __tablename__ = "security_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    auditor_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=False)
    code_audit_result = Column(JSONB, nullable=True)
    compliance_result = Column(JSONB, nullable=True)
    penetration_test_result = Column(JSONB, nullable=True)
    vulnerabilities_found = Column(Integer, nullable=False, default=0)
    vulnerabilities_fixed = Column(Integer, nullable=False, default=0)
    overall_status = Column(String(20), nullable=False, default="in_progress")
    report_content = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", foreign_keys=[project_id])
    auditor = relationship("Agent", foreign_keys=[auditor_agent_id])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "auditor_agent_id": self.auditor_agent_id,
            "code_audit_result": self.code_audit_result,
            "compliance_result": self.compliance_result,
            "penetration_test_result": self.penetration_test_result,
            "vulnerabilities_found": self.vulnerabilities_found,
            "vulnerabilities_fixed": self.vulnerabilities_fixed,
            "overall_status": self.overall_status,
            "report_content": self.report_content,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }