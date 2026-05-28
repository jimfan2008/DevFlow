"""v4.0 - 16步流程调度 API"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.services.workflow_engine import WorkflowEngine, get_default_steps

router = APIRouter(redirect_slashes=False)


class CoreGoalRequest(BaseModel):
    core_goal: str


class QAResultRequest(BaseModel):
    result: str = "passed"
    reason: Optional[str] = None
    suggestions: Optional[list[str]] = None


class UserSatisfactionRequest(BaseModel):
    satisfied: bool = True
    feedback: Optional[str] = None


class TDDPlanRequest(BaseModel):
    plan_content: dict


class CodePlanRequest(BaseModel):
    plan_content: dict
    dependency_graph: Optional[dict] = None


_wf_engines: dict[str, WorkflowEngine] = {}


def _get_engine(project_id: str) -> WorkflowEngine:
    if project_id not in _wf_engines:
        _wf_engines[project_id] = WorkflowEngine(project_id=project_id)
    return _wf_engines[project_id]


@router.post("/{project_id}/step2")
def execute_step2(project_id: str, body: CoreGoalRequest):
    engine = _get_engine(project_id)
    engine.advance_step(2)
    step = engine.complete_step(2, artifacts={"core_goal": body.core_goal})
    result = engine.pass_qa(2)
    return {"message": "第二步完成：核心目标确认与组织架构搭建", "step": step.__dict__, "qa": result.__dict__}


@router.post("/{project_id}/step3")
def execute_step3(project_id: str, body: Optional[dict] = None):
    engine = _get_engine(project_id)
    engine.advance_step(3)
    step = engine.complete_step(3, artifacts=body or {})
    return {"message": "第三步：需求分析进行中", "step": step.__dict__}


@router.post("/{project_id}/step3/qa")
def qa_step3(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(3)
    else:
        result = engine.fail_qa(3, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第三步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step4")
def execute_step4(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(4)
    step = engine.complete_step(4)
    return {"message": "第四步：架构设计进行中", "step": step.__dict__}


@router.post("/{project_id}/step4/qa")
def qa_step4(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(4)
    else:
        result = engine.fail_qa(4, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第四步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step5")
def execute_step5(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(5)
    step = engine.complete_step(5)
    return {"message": "第五步：开发环境建立中", "step": step.__dict__}


@router.post("/{project_id}/step5/qa")
def qa_step5(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(5)
    else:
        result = engine.fail_qa(5, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第五步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step6")
def execute_step6(project_id: str, body: TDDPlanRequest):
    engine = _get_engine(project_id)
    engine.advance_step(6)
    step = engine.complete_step(6, artifacts={"tdd_plan": body.plan_content})
    return {"message": "第六步：TDD测试用例计划制订完成", "step": step.__dict__}


@router.post("/{project_id}/step6/qa")
def qa_step6(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(6)
    else:
        result = engine.fail_qa(6, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第六步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step7")
def execute_step7(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(7)
    step = engine.complete_step(7)
    return {"message": "第七步：后发蜂群编写TDD测试用例", "step": step.__dict__}


@router.post("/{project_id}/step7/qa")
def qa_step7(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(7)
    else:
        result = engine.fail_qa(7, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第七步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step8")
def execute_step8(project_id: str, body: CodePlanRequest):
    engine = _get_engine(project_id)
    engine.advance_step(8)
    step = engine.complete_step(8, artifacts={"code_plan": body.plan_content, "dependency_graph": body.dependency_graph})
    return {"message": "第八步：代码编写计划制订完成", "step": step.__dict__}


@router.post("/{project_id}/step8/qa")
def qa_step8(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(8)
    else:
        result = engine.fail_qa(8, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第八步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step9")
def execute_step9(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(9)
    step = engine.complete_step(9)
    return {"message": "第九步：后发蜂群编写功能代码", "step": step.__dict__}


@router.post("/{project_id}/step9/qa")
def qa_step9(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(9)
    else:
        result = engine.fail_qa(9, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第九步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step10")
def execute_step10(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(10)
    step = engine.complete_step(10)
    return {"message": "第十步：测试环境部署完成", "step": step.__dict__}


@router.post("/{project_id}/step11")
def execute_step11(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(11)
    step = engine.complete_step(11)
    return {"message": "第十一步：后达蜂群全面测试", "step": step.__dict__}


@router.post("/{project_id}/step11/qa")
def qa_step11(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(11)
    else:
        result = engine.fail_qa(11, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第十一步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step12")
def execute_step12(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(12)
    step = engine.complete_step(12)
    return {"message": "第十二步：后华安全审计", "step": step.__dict__}


@router.post("/{project_id}/step12/qa")
def qa_step12(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(12)
    else:
        result = engine.fail_qa(12, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第十二步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step13")
def execute_step13(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(13)
    step = engine.complete_step(13)
    return {"message": "第十三步：生产环境部署完成", "step": step.__dict__}


@router.post("/{project_id}/step14")
def execute_step14(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(14)
    step = engine.complete_step(14)
    return {"message": "第十四步：后贵完善项目文档", "step": step.__dict__}


@router.post("/{project_id}/step14/qa")
def qa_step14(project_id: str, body: QAResultRequest):
    engine = _get_engine(project_id)
    if body.result == "passed":
        result = engine.pass_qa(14)
    else:
        result = engine.fail_qa(14, reason=body.reason or "", suggestions=body.suggestions)
    return {"message": f"第十四步QA检验{'通过' if body.result == 'passed' else '未通过'}", "qa": result.__dict__}


@router.post("/{project_id}/step15")
def execute_step15(project_id: str):
    engine = _get_engine(project_id)
    engine.advance_step(15)
    step = engine.complete_step(15)
    return {"message": "第十五步：海梅报告交付成果", "step": step.__dict__}


@router.post("/{project_id}/step16")
def execute_step16(project_id: str, body: UserSatisfactionRequest):
    engine = _get_engine(project_id)
    if body.satisfied:
        engine.advance_step(16)
        step = engine.complete_step(16)
        return {"message": "项目完成！用户确认满意，项目结束", "step": step.__dict__}
    else:
        result = engine.user_dissatisfied(feedback=body.feedback or "用户不满意")
        return {"message": "用户不满意，回到第三步重新迭代", "iteration": result}


@router.get("/{project_id}/status")
def get_project_status(project_id: str):
    engine = _get_engine(project_id)
    return engine.get_current_status()