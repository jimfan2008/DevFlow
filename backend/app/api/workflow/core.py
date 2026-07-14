"""v4.0 - 16步流程调度 API（DB持久化）"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import Optional, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.workflow_engine import WorkflowEngine, get_default_steps
from app.core.responses import APIResponse
from app.api.deps import get_current_user
from app.config import settings
import asyncio
import os
import logging

logger = logging.getLogger("devflow.workflow")

router = APIRouter(redirect_slashes=False)


def build_output_dirs(slug: str) -> Dict[str, str]:
    """构建项目输出目录映射，供 agent system prompt 使用"""
    return {
        "docs": os.path.join(settings.PROJECTS_BASE_DIR, slug, settings.PROJECT_DOCS_SUBDIR),
        "tmp": os.path.join(settings.PROJECTS_BASE_DIR, slug, settings.PROJECT_TMP_SUBDIR),
    }


class CoreGoalRequest(BaseModel):
    core_goal: str


class Step2ArtifactsRequest(BaseModel):
    phase: str
    core_goal: str = ""
    confirmed_goal: str = ""
    chat_round: int = 0
    messages: list = []
    agents: list = []
    group_info: Optional[dict] = None
    qa_passed: bool = False
    qa_message: str = ""


class QAResultRequest(BaseModel):
    result: str = "passed"
    reason: Optional[str] = None
    suggestions: Optional[list[str]] = None


class UserSatisfactionRequest(BaseModel):
    satisfied: bool = True
    feedback: Optional[str] = None


class Step3InspectRequest(BaseModel):
    content: str
    filename: Optional[str] = None
    focus_items: Optional[list[str]] = None
    save_path: Optional[str] = None


class TDDPlanRequest(BaseModel):
    plan_content: dict


class CodePlanRequest(BaseModel):
    plan_content: dict
    dependency_graph: Optional[dict] = None


class Step5ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step7ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step9ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step10ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step11ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step12ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step13ChatRequest(BaseModel):
    message: str
    messages: list = []


class Step14ChatRequest(BaseModel):
    message: str
    messages: list = []


class DocsListRequest(BaseModel):
    path: str


class MobilizeAgentRequest(BaseModel):
    step_number: int


_wf_engines: dict[str, WorkflowEngine] = {}


def _get_engine(project_id: str, db: Session) -> WorkflowEngine:
    # 校验项目是否存在
    from app.models.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        # 项目不存在，查找同名的其他项目
        all_projects = db.query(Project).all()
        if all_projects:
            proj_names = ", ".join([f"{p.name}({p.id})" for p in all_projects[:5]])
            raise Exception(
                f"项目不存在 (ID: {project_id})。"
                f"当前项目列表: {proj_names}"
            )
        raise Exception(f"项目不存在 (ID: {project_id})。当前没有项目，请先创建项目。")
    
    if project_id not in _wf_engines:
        _wf_engines[project_id] = WorkflowEngine(project_id=project_id, db=db, auto_supervise=True)
    else:
        _wf_engines[project_id].db = db
        _wf_engines[project_id]._load_from_db()
        # 海梅每次获取引擎时自动检查和推进项目
        try:
            _wf_engines[project_id].haimei_auto_advance()
        except Exception:
            pass
    return _wf_engines[project_id]





@router.get("/{project_id}/status")
async def get_project_status(project_id: str,
                             db: Session = Depends(get_db),
                             current_user=Depends(get_current_user)):
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.get_current_status())


@router.delete("/{project_id}/cache")
def clear_engine_cache(project_id: str,
                       db: Session = Depends(get_db),
                       current_user=Depends(get_current_user)):
    _wf_engines.pop(project_id, None)
    return APIResponse(code=0, data={"message": "引擎缓存已清除"})


# ============================================================
# 海梅(HaiMei) 项目经理全程监控 API
# ============================================================

@router.get("/{project_id}/haimei/supervise")
def haimei_supervise_project(project_id: str,
                              db: Session = Depends(get_db),
                              current_user=Depends(get_current_user)):
    """海梅全面检查项目推进状态"""
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.haimei_check_project_progress())


@router.get("/{project_id}/haimei/agents")
def haimei_check_agents(project_id: str,
                         db: Session = Depends(get_db),
                         current_user=Depends(get_current_user)):
    """海梅检查所有Agent健康状态"""
    engine = _get_engine(project_id, db)
    return APIResponse(code=0, data=engine.haimei_get_all_agent_statuses())


@router.get("/{project_id}/haimei/agent/{agent_role}/health")
def haimei_check_single_agent(project_id: str, agent_role: str,
                               db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    """海梅检查单个Agent健康状态"""
    engine = _get_engine(project_id, db)
    health = engine.haimei_check_agent_health(agent_role)
    return APIResponse(code=0, data={
        "agent": agent_role,
        "health": health,
    })


@router.post("/{project_id}/haimei/agent/{agent_role}/restore")
def haimei_restore_agent(project_id: str, agent_role: str,
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    """海梅恢复异常Agent到正常工作状态"""
    engine = _get_engine(project_id, db)
    result = engine.haimei_restore_agent(agent_role)
    return APIResponse(code=0, data=result)


@router.post("/{project_id}/haimei/step/{step_number}/supervise")
def haimei_supervise_step(project_id: str, step_number: int,
                           db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    """海梅对特定步骤进行前置监督审查"""
    engine = _get_engine(project_id, db)
    result = engine.haimei_supervise_step(step_number)
    return APIResponse(code=0, data=result)


@router.post("/{project_id}/haimei/step/{step_number}/restart")
def haimei_force_restart_step(project_id: str, step_number: int,
                               db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    """海梅强制重启异常步骤（恢复Agent并重置状态）"""
    engine = _get_engine(project_id, db)
    result = engine.haimei_force_restart_step(step_number)
    return APIResponse(code=0, data=result)


@router.post("/{project_id}/haimei/mobilize")
def haimei_mobilize_agent(project_id: str, body: MobilizeAgentRequest,
                           db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    """海梅调动指定Agent执行某一步骤"""
    engine = _get_engine(project_id, db)
    result = engine.haimei_mobilize_agent(body.step_number)
    return APIResponse(code=0, data=result)


@router.get("/{project_id}/haimei/board-data")
def haimei_get_board_data(project_id: str,
                           board_id: Optional[str] = None,
                           db: Session = Depends(get_db),
                           current_user=Depends(get_current_user)):
    """海梅采集工作流数据并返回看板展示内容"""
    from app.services.haimei_board_sync import HaimeiBoardSyncService
    from app.models.project import Project

    if not board_id:
        from app.models.board import Board
        board = db.query(Board).filter(Board.project_id == project_id).first()
        board_id = board.id if board else None

    sync_service = HaimeiBoardSyncService(db)
    data = sync_service.get_workflow_board_data(project_id, board_id)
    return APIResponse(code=0, data=data)


@router.post("/{project_id}/haimei/sync-board")
def haimei_sync_to_board(project_id: str,
                          board_id: str = Body(..., embed=True),
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    """海梅将工作流数据同步到看板任务"""
    from app.services.haimei_board_sync import HaimeiBoardSyncService
    sync_service = HaimeiBoardSyncService(db)
    result = sync_service.sync_workflow_to_board(project_id, board_id)
    return APIResponse(code=0, data=result)


@router.post("/{project_id}/haimei/auto-advance")
def haimei_auto_advance_project(project_id: str,
                                 db: Session = Depends(get_db),
                                 current_user=Depends(get_current_user)):
    """海梅自主推进项目：自动检查所有步骤状态、恢复异常Agent、推进下一个就绪步骤"""
    engine = _get_engine(project_id, db)
    result = engine.haimei_auto_advance()
    return APIResponse(code=0, data=result)


@router.get("/{project_id}/haimei/task-list")
def haimei_get_task_list(project_id: str,
                          db: Session = Depends(get_db),
                          current_user=Depends(get_current_user)):
    """海梅生成项目任务清单（16步流程的完整任务列表）"""
    engine = _get_engine(project_id, db)
    task_list = engine.haimei_generate_task_list()
    return APIResponse(code=0, data={
        "project_id": project_id,
        "task_list": task_list,
        "total_tasks": len(task_list),
        "generated_by": "haimei",
        "haimei_message": "海梅已生成项目任务清单，共{}项任务".format(len(task_list)),
    })


@router.get("/{project_id}/haimei/report")
def haimei_get_project_report(project_id: str,
                               db: Session = Depends(get_db),
                               current_user=Depends(get_current_user)):
    """海梅生成完整的项目推进报告"""
    engine = _get_engine(project_id, db)
    report = engine.haimei_get_report()
    return APIResponse(code=0, data=report)


ARCH_DESIGN_DIMENSIONS = [
    {"key": "arch_reasonableness", "label": "架构合理性", "description": "架构设计是否合理，是否满足需求文档中的功能和非功能需求"},
    {"key": "frontend_feasibility", "label": "前端可行性", "description": "前端设计方案是否可行，技术选型是否合理"},
    {"key": "backend_feasibility", "label": "后端可行性", "description": "后端设计方案是否可行，API设计是否合理"},
    {"key": "database_design", "label": "数据库设计", "description": "数据库设计是否规范，ER关系是否清晰"},
]

CODE_INSPECTION_DIMENSIONS = [
    {"key": "code_correctness", "label": "代码正确性", "description": "代码逻辑是否正确"},
    {"key": "test_pass_rate", "label": "测试用例通过率", "description": "测试用例通过率"},
    {"key": "requirement_match", "label": "需求匹配度", "description": "代码是否满足需求"},
    {"key": "code_standard", "label": "代码规范", "description": "命名规范、注释、代码风格"},
]

ENV_SETUP_DIMENSIONS = [
    {"key": "environment_availability", "label": "环境可用性", "description": "开发环境是否可正常运行"},
    {"key": "config_correctness", "label": "配置正确性", "description": "配置文件是否完整、正确"},
    {"key": "dependency_completeness", "label": "依赖完整性", "description": "依赖包、工具链是否齐全"},
]

TDD_PLAN_DIMENSIONS = [
    {"key": "coverage", "label": "需求覆盖率", "description": "是否覆盖所有功能需求"},
    {"key": "atomicity", "label": "原子化程度", "description": "每个测试用例是否最小不可再分"},
    {"key": "measurability", "label": "验收标准可量化性", "description": "验收标准是否可量化、可验证"},
]

TDD_TESTCASE_DIMENSIONS = [
    {"key": "correctness", "label": "用例正确性", "description": "测试逻辑是否正确"},
    {"key": "coverage", "label": "需求覆盖率", "description": "是否覆盖所有功能需求"},
    {"key": "atomicity", "label": "原子化程度", "description": "每个测试用例是否最小不可再分"},
    {"key": "acceptance_match", "label": "验收标准匹配度", "description": "测试用例与验收标准是否匹配"},
]

CODE_PLAN_DIMENSIONS = [
    {"key": "task_atomicity", "label": "任务原子化", "description": "每个任务是否最小不可再分"},
    {"key": "test_mapping", "label": "测试用例对应完整性", "description": "每个任务是否有测试用例一一对应"},
    {"key": "dependency_correctness", "label": "依赖关系正确性", "description": "依赖图是否无循环"},
]

TEST_INSPECTION_DIMENSIONS = [
    {"key": "test_coverage", "label": "测试覆盖率", "description": "是否覆盖所有功能点"},
    {"key": "pass_rate", "label": "测试通过率", "description": "测试通过率"},
    {"key": "defect_severity", "label": "缺陷严重程度", "description": "是否有严重缺陷未修复"},
    {"key": "practical_validation", "label": "前端实操验证结果", "description": "前端实操验证结果"},
]

SECURITY_INSPECTION_DIMENSIONS = [
    {"key": "vulnerability_fix_rate", "label": "漏洞修复率", "description": "高危漏洞是否全部修复"},
    {"key": "compliance", "label": "合规达标率", "description": "是否符合行业规范和法规"},
    {"key": "penetration_test", "label": "渗透测试通过情况", "description": "渗透测试通过情况"},
]

DOC_INSPECTION_DIMENSIONS = [
    {"key": "doc_completeness", "label": "文档完整性", "description": "是否包含部署手册/操作手册/API文档/用户手册"},
    {"key": "doc_consistency", "label": "文档间一致性", "description": "文档之间是否相互一致，有无矛盾"},
    {"key": "doc_accuracy", "label": "描述准确性", "description": "文档描述是否与代码实现一致"},
]

DEPLOY_TEST_DIMENSIONS = [
    {"key": "deploy_config", "label": "部署配置", "description": "测试环境部署配置是否正确完整"},
    {"key": "env_compatibility", "label": "环境兼容性", "description": "与开发测试环境是否兼容一致"},
    {"key": "service_availability", "label": "服务可用性", "description": "部署后服务是否可正常启动和访问"},
]

DEPLOY_PROD_DIMENSIONS = [
    {"key": "prod_config", "label": "生产配置", "description": "生产环境配置是否正确"},
    {"key": "safety_guard", "label": "安全防护", "description": "是否有适当的安全防护措施"},
    {"key": "rollback_plan", "label": "回滚方案", "description": "回滚方案是否完整可行"},
    {"key": "service_stability", "label": "服务稳定性", "description": "部署后系统是否稳定运行"},
]


