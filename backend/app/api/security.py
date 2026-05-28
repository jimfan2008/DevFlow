"""v4.0 - 安全审计 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

router = APIRouter(redirect_slashes=False)


class AuditReport(BaseModel):
    project_id: str
    auditor_agent_id: str = ""
    code_audit: Optional[dict] = None
    compliance: Optional[dict] = None
    penetration_test: Optional[dict] = None
    vulnerabilities_found: int = 0
    vulnerabilities_fixed: int = 0
    overall_status: str = "in_progress"


_audits: dict[str, dict] = {}


@router.post("/{project_id}/audit")
def start_audit(project_id: str, body: AuditReport):
    audit = {
        "project_id": project_id,
        "auditor_agent_id": body.auditor_agent_id,
        "code_audit_result": body.code_audit,
        "compliance_result": body.compliance,
        "penetration_test_result": body.penetration_test,
        "vulnerabilities_found": body.vulnerabilities_found,
        "vulnerabilities_fixed": body.vulnerabilities_fixed,
        "overall_status": body.overall_status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    _audits[project_id] = audit
    return {"message": "安全审计已启动", "audit": audit}


@router.get("/{project_id}/audit/status")
def get_audit_status(project_id: str):
    audit = _audits.get(project_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="安全审计记录不存在")
    return {
        "project_id": project_id,
        "status": audit["overall_status"],
        "vulnerabilities_found": audit["vulnerabilities_found"],
        "vulnerabilities_fixed": audit["vulnerabilities_fixed"],
    }


@router.get("/{project_id}/audit/report")
def get_audit_report(project_id: str):
    audit = _audits.get(project_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="安全审计记录不存在")
    return audit