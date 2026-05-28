"""v4.0 - QA 门控检验服务"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


class QAGateService:
    INSPECTION_DIMENSIONS = {
        "core_goal": ["目标明确性", "组织完整性", "讨论群建立状态"],
        "srs": ["完整性", "一致性", "可验证性", "无歧义性"],
        "design": ["设计完整性", "需求覆盖度", "技术可行性", "架构合理性"],
        "dev_env": ["可用性", "配置正确性", "依赖完整性"],
        "tdd_plan": ["覆盖率", "原子化程度", "验收标准可量化性"],
        "tdd_code": ["正确性", "覆盖率", "原子化", "验收标准匹配"],
        "code_plan": ["任务原子化", "测试用例对应完整性", "依赖关系正确性"],
        "function_code": ["正确性", "测试通过率", "需求匹配度", "代码规范"],
        "test_report": ["覆盖率", "通过率", "缺陷严重度", "实操验证结果"],
        "security_audit": ["漏洞修复率", "合规达标", "渗透测试通过情况"],
        "project_docs": ["完整性", "文档间一致性", "描述准确性"],
    }

    def __init__(self):
        self._records: List[Dict[str, Any]] = []
        self._next_record_id = 1

    def inspect(self, artifact_type: str, project_id: str, workflow_step_id: int,
                result: str = "passed", reason: Optional[str] = None,
                suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
        if artifact_type not in self.INSPECTION_DIMENSIONS:
            raise ValueError(f"未知的产出类型: {artifact_type}")

        dimensions = list(self.INSPECTION_DIMENSIONS[artifact_type])

        record = {
            "id": self._next_record_id,
            "project_id": project_id,
            "workflow_step_id": workflow_step_id,
            "artifact_type": artifact_type,
            "status": result,
            "review_dimensions": dimensions,
            "problem_details": reason,
            "fix_suggestions": suggestions or [],
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        }
        self._next_record_id += 1
        self._records.append(record)
        return dict(record)

    def rollback(self, task_id: str, project_id: str, workflow_step_id: int,
                 reason: str, suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
        record = {
            "id": self._next_record_id,
            "project_id": project_id,
            "workflow_step_id": workflow_step_id,
            "task_id": task_id,
            "status": "failed",
            "review_dimensions": [],
            "problem_details": reason,
            "fix_suggestions": suggestions or [],
            "inspected_at": datetime.now(timezone.utc).isoformat(),
        }
        self._next_record_id += 1
        self._records.append(record)
        return dict(record)

    def get_inspection_status(self, task_id: Optional[str] = None,
                               step_id: Optional[int] = None) -> Dict[str, Any]:
        relevant = self._records
        if task_id is not None:
            relevant = [r for r in relevant if r.get("task_id") == task_id]
        if step_id is not None:
            relevant = [r for r in relevant if r.get("workflow_step_id") == step_id]

        return {
            "task_id": task_id,
            "step_id": step_id,
            "records_count": len(relevant),
            "latest_status": relevant[-1]["status"] if relevant else "unknown",
            "records": [dict(r) for r in relevant],
        }

    def get_all_records(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if project_id:
            return [dict(r) for r in self._records if r["project_id"] == project_id]
        return [dict(r) for r in self._records]