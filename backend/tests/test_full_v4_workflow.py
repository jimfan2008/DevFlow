"""v4.0 - 全流程集成测试"""
import pytest
from app.services.workflow_engine import (
    WorkflowEngine, StepDefinition, get_default_steps, QARecordResult, StepRecord
)
from app.services.swarm_service import SwarmService, SUPPORTED_SWARM_AGENTS
from app.services.qa_gate_service import QAGateService
from app.services.agent_role_service import AgentRoleService, NAMED_ROLES


class TestComplete16StepFlow:
    """完整16步流程测试"""

    def test_full_workflow_step_by_step(self):
        engine = WorkflowEngine(project_id="test-project-001")
        assert engine.current_step == 1
        assert engine._step_states[1].status == "completed"

        # Step 2: 海梅确认核心目标 + 搭建组织架构 + 建立讨论群
        engine.advance_step(2)
        assert engine.current_step == 2
        assert engine._step_states[2].status == "in_progress"
        engine.complete_step(2, artifacts={"core_goal": "构建DevFlow全自动开发平台", "org_structure": "9人团队", "discussion_group": "project-001-group"})
        assert engine._step_states[2].status == "qa_review"
        record = engine.pass_qa(2, qa_agent_id="hourong")
        assert record.status == "passed"
        assert engine._step_states[2].status == "completed"

        # Step 3: 后兴需求分析
        engine.advance_step(3)
        engine.complete_step(3, artifacts={"srs": "软件需求规格说明书v1.0"})
        record = engine.pass_qa(3)
        assert record.status == "passed"

        # Step 4: 后旺架构设计 (4份设计文档)
        engine.advance_step(4)
        engine.complete_step(4, artifacts={
            "architecture_design": "架构设计文档",
            "backend_design": "后端设计文档",
            "frontend_design": "前端设计文档",
            "database_design": "数据库设计文档",
        })
        record = engine.pass_qa(4)
        assert record.status == "passed"

        # Step 5: 后富建立开发环境
        engine.advance_step(5)
        engine.complete_step(5, artifacts={"dev_env": "开发环境就绪"})
        record = engine.pass_qa(5)
        assert record.status == "passed"

        # Step 6: 海梅制订TDD测试用例计划
        engine.advance_step(6)
        engine.complete_step(6, artifacts={"tdd_plan": "TDD测试用例编写计划"})
        record = engine.pass_qa(6)
        assert record.status == "passed"

        # Step 7: 后发蜂群编写TDD测试用例
        engine.advance_step(7)
        engine.complete_step(7, artifacts={"tdd_test_cases": "所有TDD测试用例代码"})
        record = engine.pass_qa(7)
        assert record.status == "passed"

        # Step 8: 海梅制订代码编写计划 (含任务依赖图)
        engine.advance_step(8)
        engine.complete_step(8, artifacts={
            "code_plan": "代码编写计划",
            "dependency_graph": "有向无环图",
        })
        record = engine.pass_qa(8)
        assert record.status == "passed"

        # Step 9: 后发蜂群编写功能代码
        engine.advance_step(9)
        engine.complete_step(9, artifacts={"function_code": "全部功能代码"})
        record = engine.pass_qa(9)
        assert record.status == "passed"

        # Step 10: 后富部署到测试环境 (不需要QA)
        engine.advance_step(10)
        engine.complete_step(10, artifacts={"test_env": "测试环境部署成功"})
        assert engine._step_states[10].status == "completed"

        # Step 11: 后达蜂群全面测试
        engine.advance_step(11)
        engine.complete_step(11, artifacts={
            "unit_test_report": "单元测试通过",
            "module_test_report": "模块测试通过",
            "integration_test_report": "集成测试通过",
            "frontend_verification": "前端实操验证通过",
        })
        record = engine.pass_qa(11)
        assert record.status == "passed"

        # Step 12: 后华安全审计
        engine.advance_step(12)
        engine.complete_step(12, artifacts={
            "security_audit": "安全审计报告",
            "vulnerabilities_fixed": 3,
        })
        record = engine.pass_qa(12)
        assert record.status == "passed"

        # Step 13: 后富部署到生产环境 (不需要QA)
        engine.advance_step(13)
        engine.complete_step(13, artifacts={"prod_env": "生产环境部署成功"})
        assert engine._step_states[13].status == "completed"

        # Step 14: 后贵完善项目文档
        engine.advance_step(14)
        engine.complete_step(14, artifacts={
            "deployment_manual": "部署手册",
            "operation_manual": "操作手册",
            "api_documentation": "API文档",
            "user_manual": "用户手册",
        })
        record = engine.pass_qa(14)
        assert record.status == "passed"

        # Step 15: 海梅报告交付成果 (不需要QA)
        engine.advance_step(15)
        engine.complete_step(15, artifacts={"delivery_report": "项目交付报告"})
        assert engine._step_states[15].status == "completed"

        # Step 16: 用户满意度确认
        engine.advance_step(16)
        engine.complete_step(16, artifacts={"user_satisfied": True})
        assert engine._step_states[16].status == "completed"

        # 验证流程完整性
        assert engine.current_step == 16
        status = engine.get_current_status()
        assert status["current_step"] == 16
        assert status["qa_records_count"] == 11  # 需要QA的步骤共11个

    def test_all_qa_required_steps_receive_qa(self):
        engine = WorkflowEngine(project_id="test-project-002")
        qa_steps = engine.QA_REQUIRED_STEPS

        for step_num in range(2, 17):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={f"step_{step_num}_output": "done"})
            if step_num in qa_steps:
                engine.pass_qa(step_num)

        status = engine.get_current_status()
        assert status["qa_records_count"] == len(qa_steps)

    def test_step_status_transitions(self):
        engine = WorkflowEngine(project_id="test-project-003")
        engine.advance_step(2)
        assert engine._step_states[2].status == "in_progress"

        engine.complete_step(2)
        assert engine._step_states[2].status == "qa_review"

        engine.pass_qa(2)
        assert engine._step_states[2].status == "completed"

    def test_artifacts_preserved_after_qa(self):
        engine = WorkflowEngine(project_id="test-project-004")
        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "完整项目目标"})
        engine.pass_qa(2)

        preserved = engine.get_preserved_artifacts()
        assert "step_2" in preserved
        assert preserved["step_2"]["core_goal"] == "完整项目目标"


class TestIterationLoop:
    """迭代修改闭环测试"""

    def test_step16_dissatisfaction_resets_to_step3(self):
        engine = WorkflowEngine(project_id="test-project-iter-001")

        for step_num in range(2, 16):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={f"step_{step_num}": "done"})
            if step_num in engine.QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)

        engine.advance_step(16)
        result = engine.user_dissatisfied("功能不完整，需要增加导出功能")

        assert result["reset_from_step"] == 3
        assert result["current_step"] == 3
        assert engine.current_step == 3

    def test_reiterate_preserves_early_steps(self):
        engine = WorkflowEngine(project_id="test-project-iter-002")

        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "核心目标V1"})
        engine.pass_qa(2)

        preserved = engine.get_preserved_artifacts()
        assert "step_2" in preserved

        engine.user_dissatisfied("需要修改")

        preserved_after = engine.get_preserved_artifacts()
        assert "step_2" in preserved_after
        assert preserved_after["step_2"]["core_goal"] == "核心目标V1"

    def test_step3_16_reset_after_iteration(self):
        engine = WorkflowEngine(project_id="test-project-iter-003")

        for step_num in range(2, 11):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={f"step_{step_num}": "done"})
            if step_num in engine.QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)

        engine.user_dissatisfied("不满意")

        for step_num in range(3, 17):
            assert engine._step_states[step_num].status == "pending"

    def test_multiple_iterations(self):
        engine = WorkflowEngine(project_id="test-project-iter-004")

        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)

        iter_count = 0
        for _ in range(3):
            engine.advance_step(3)
            engine.complete_step(3, artifacts={"srs": f"SRS 迭代{iter_count}"})
            engine.pass_qa(3)
            engine.user_dissatisfied(f"迭代{iter_count}不满意")
            iter_count += 1

        history = engine.get_step_history()
        iteration_entries = [h for h in history if h.get("status") == "iterating"]
        assert len(iteration_entries) == 3
        assert engine.current_step == 3


class TestQARejection:
    """QA驳回重做测试"""

    def test_qa_rejection_mid_flow(self):
        engine = WorkflowEngine(project_id="test-project-qa-001")

        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "模糊目标"})
        record = engine.fail_qa(2, reason="核心目标不够明确", suggestions=["请细化功能边界", "补充非功能需求"])
        assert record.status == "failed"
        assert engine._step_states[2].status == "rejected"
        assert record.problem_details == "核心目标不够明确"

        engine.complete_step(2, artifacts={"core_goal": "明确核心目标", "non_functional": "补充非功能需求"})
        assert engine._step_states[2].status == "qa_review"
        record2 = engine.pass_qa(2)
        assert record2.status == "passed"

        engine.advance_step(3)
        assert engine.current_step == 3

    def test_design_step_each_doc_qa(self):
        engine = WorkflowEngine(project_id="test-project-qa-002")

        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)
        engine.advance_step(3)
        engine.complete_step(3)
        engine.pass_qa(3)

        engine.advance_step(4)
        engine.complete_step(4, artifacts={
            "architecture_design": "架构设计草图",
            "backend_design": "后端设计",
            "frontend_design": "前端设计",
            "database_design": "数据库设计",
        })

        fail_record = engine.fail_qa(4, reason="架构设计不够合理", suggestions=["请重新评估微服务拆分方案"])
        assert fail_record.status == "failed"
        assert engine._step_states[4].status == "rejected"

        engine.complete_step(4, artifacts={
            "architecture_design": "架构设计优化版",
            "backend_design": "后端设计优化版",
            "frontend_design": "前端设计",
            "database_design": "数据库设计",
        })
        pass_record = engine.pass_qa(4)
        assert pass_record.status == "passed"

    def test_qa_rejection_suggestions_preserved(self):
        engine = WorkflowEngine(project_id="test-project-qa-003")

        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)

        engine.advance_step(3)
        engine.complete_step(3, artifacts={"srs": "不完整的SRS"})
        engine.fail_qa(3, reason="缺少验收标准", suggestions=["补充功能验收标准", "补充性能验收标准"])

        engine.complete_step(3, artifacts={"srs": "完整SRS", "acceptance_criteria": "详细验收标准"})
        engine.pass_qa(3)

        history = engine.get_step_history()
        step3_entries = [h for h in history if h["step_number"] == 3]
        assert len(step3_entries) >= 3  # complete → fail → complete → pass

    def test_cannot_advance_after_rejection(self):
        engine = WorkflowEngine(project_id="test-project-qa-004")

        engine.advance_step(2)
        engine.complete_step(2)
        engine.fail_qa(2, reason="不合格")

        with pytest.raises(ValueError, match="必须通过QA检验"):
            engine.advance_step(3)


class TestSwarmIntegration:
    """蜂群集成测试"""

    def test_swarm_creation_and_task_dispatch(self):
        service = SwarmService()

        swarm = service.create_swarm(
            project_id="test-project-swarm-001",
            name="前端代码编写蜂群",
            purpose="code_writing",
            step_number=9,
            manager_role="houfa",
        )
        assert swarm["purpose"] == "code_writing"
        assert swarm["manager_role"] == "houfa"
        assert swarm["status"] == "active"

        service.add_member(swarm["id"], "claude_code", "claude-1")
        service.add_member(swarm["id"], "opencode", "opencode-1")
        service.add_member(swarm["id"], "cursor", "cursor-1")

        tasks = [
            {"task_id": "task-1", "name": "用户登录模块"},
            {"task_id": "task-2", "name": "项目列表页面"},
            {"task_id": "task-3", "name": "任务管理接口"},
            {"task_id": "task-4", "name": "通知服务"},
            {"task_id": "task-5", "name": "文件上传"},
        ]
        assignments = service.dispatch_tasks(swarm["id"], tasks)
        assert len(assignments) == 5

        assigned_agents = {a["assigned_agent_id"] for a in assignments}
        assert len(assigned_agents) >= 2  # 至少分配给2个不同Agent

        progress = service.get_progress(swarm["id"])
        assert progress["total_tasks"] == 5
        assert progress["completed_tasks"] == 0

    def test_swarm_dependency_aware_dispatch(self):
        service = SwarmService()

        swarm = service.create_swarm(
            project_id="test-project-swarm-002",
            name="后端代码蜂群",
            purpose="code_writing",
            step_number=9,
            manager_role="houfa",
        )
        service.add_member(swarm["id"], "claude_code", "claude-1")
        service.add_member(swarm["id"], "codex", "codex-1")

        tasks = [
            {"task_id": "task-a", "name": "数据库模型"},
            {"task_id": "task-b", "name": "API接口", "depends_on": ["task-a"]},
            {"task_id": "task-c", "name": "业务逻辑", "depends_on": ["task-b"]},
        ]
        assignments = service.dispatch_tasks(swarm["id"], tasks)

        # task-b和task-a应该分配给不同的Agent（有依赖关系）
        task_a_agent = assignments[0]["assigned_agent_id"]
        task_b_agent = assignments[1]["assigned_agent_id"]
        assert task_a_agent != task_b_agent, "有依赖关系的任务应分配给不同Agent"

    def test_swarm_manager_role_restrictions(self):
        service = SwarmService()

        with pytest.raises(ValueError, match="后发只能建立代码编写蜂群"):
            service.create_swarm(
                project_id="test-project-swarm-003",
                name="错误蜂群",
                purpose="test_execution",
                step_number=11,
                manager_role="houfa",
            )

        with pytest.raises(ValueError, match="后达只能建立测试蜂群"):
            service.create_swarm(
                project_id="test-project-swarm-004",
                name="错误蜂群",
                purpose="code_writing",
                step_number=7,
                manager_role="houda",
            )

    def test_test_swarm_creation(self):
        service = SwarmService()

        swarm = service.create_swarm(
            project_id="test-project-swarm-005",
            name="集成测试蜂群",
            purpose="test_execution",
            step_number=11,
            manager_role="houda",
        )
        assert swarm["purpose"] == "test_execution"
        assert swarm["manager_role"] == "houda"

        service.add_member(swarm["id"], "trae", "trae-1")
        service.add_member(swarm["id"], "lingma", "lingma-1")

        tasks = [
            {"task_id": "test-unit", "name": "单元测试"},
            {"task_id": "test-integration", "name": "集成测试"},
            {"task_id": "test-e2e", "name": "端到端测试"},
        ]
        assignments = service.dispatch_tasks(swarm["id"], tasks)
        assert len(assignments) == 3

    def test_swarm_disband(self):
        service = SwarmService()

        swarm = service.create_swarm(
            project_id="test-project-swarm-006",
            name="临时蜂群",
            purpose="code_writing",
            step_number=7,
            manager_role="houfa",
        )
        result = service.disband_swarm(swarm["id"])
        assert result["status"] == "disbanded"
        assert result["disbanded_at"] is not None

    def test_swarm_complete_workflow_for_step9(self):
        engine = WorkflowEngine(project_id="test-project-swarm-007")
        swarm_service = SwarmService()

        for s in range(2, 9):
            engine.advance_step(s)
            engine.complete_step(s)
            engine.pass_qa(s)

        engine.advance_step(9)
        swarm = swarm_service.create_swarm(
            project_id="test-project-swarm-007",
            name="功能代码编写蜂群",
            purpose="code_writing",
            step_number=9,
            manager_role="houfa",
        )
        swarm_service.add_member(swarm["id"], "claude_code", "claude-1")
        swarm_service.add_member(swarm["id"], "opencode", "opencode-1")
        swarm_service.add_member(swarm["id"], "cursor", "cursor-1")

        tasks = [
            {"task_id": "code-1", "name": "用户模块"},
            {"task_id": "code-2", "name": "项目模块"},
            {"task_id": "code-3", "name": "任务模块"},
            {"task_id": "code-4", "name": "通知模块"},
            {"task_id": "code-5", "name": "文件模块"},
            {"task_id": "code-6", "name": "QA模块"},
            {"task_id": "code-7", "name": "蜂群模块"},
            {"task_id": "code-8", "name": "安全审计模块"},
        ]
        assignments = swarm_service.dispatch_tasks(swarm["id"], tasks)
        assert len(assignments) == 8

        engine.complete_step(9, artifacts={"function_code": "全部功能代码"})
        engine.pass_qa(9)
        assert engine.current_step == 9

        progress = swarm_service.get_progress(swarm["id"])
        assert progress["total_tasks"] == 8


class TestQAGateIntegration:
    """QA门控集成测试"""

    def test_qa_inspection_all_artifact_types(self):
        qa_service = QAGateService()

        artifact_types = list(qa_service.INSPECTION_DIMENSIONS.keys())
        assert len(artifact_types) == 11

        for artifact_type in artifact_types:
            result = qa_service.inspect(
                artifact_type=artifact_type,
                project_id="test-project-qa-integ-001",
                workflow_step_id=3,
                result="passed",
            )
            assert result["status"] == "passed"
            assert result["artifact_type"] == artifact_type
            dimensions = qa_service.INSPECTION_DIMENSIONS[artifact_type]
            assert len(result["review_dimensions"]) == len(dimensions)

    def test_qa_inspection_fail_with_suggestions(self):
        qa_service = QAGateService()

        result = qa_service.inspect(
            artifact_type="srs",
            project_id="test-project-qa-integ-002",
            workflow_step_id=3,
            result="failed",
            reason="缺少非功能需求章节",
            suggestions=["补充性能要求", "补充安全要求", "补充可用性要求"],
        )
        assert result["status"] == "failed"
        assert len(result["fix_suggestions"]) == 3

    def test_qa_rollback_and_reinspect(self):
        qa_service = QAGateService()

        rollback = qa_service.rollback(
            task_id="task-001",
            project_id="test-project-qa-integ-003",
            workflow_step_id=4,
            reason="架构设计不合理",
            suggestions=["重新评估技术选型"],
        )
        assert rollback["status"] == "failed"

        reinspect = qa_service.inspect(
            artifact_type="design",
            project_id="test-project-qa-integ-003",
            workflow_step_id=4,
            result="passed",
        )
        assert reinspect["status"] == "passed"

    def test_qa_records_by_project(self):
        qa_service = QAGateService()

        qa_service.inspect("srs", "proj-a", 3, "passed")
        qa_service.inspect("design", "proj-a", 4, "passed")
        qa_service.inspect("tdd_plan", "proj-b", 6, "passed")

        proj_a_records = qa_service.get_all_records("proj-a")
        assert len(proj_a_records) == 2

        proj_b_records = qa_service.get_all_records("proj-b")
        assert len(proj_b_records) == 1

    def test_qa_inspection_status_lookup(self):
        qa_service = QAGateService()

        qa_service.inspect("srs", "test-proj", 3, "passed")
        qa_service.inspect("design", "test-proj", 4, "failed", reason="架构不合理")

        status = qa_service.get_inspection_status(step_id=3)
        assert status["latest_status"] == "passed"
        assert status["records_count"] == 1

        status2 = qa_service.get_inspection_status(step_id=4)
        assert status2["latest_status"] == "failed"

    def test_qa_workflow_integration(self):
        engine = WorkflowEngine(project_id="test-project-qa-flow-001")
        qa_service = QAGateService()

        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "明确目标"})
        engine.pass_qa(2)
        qa_service.inspect("core_goal", "test-project-qa-flow-001", 2, "passed")

        engine.advance_step(3)
        engine.complete_step(3, artifacts={"srs": "需求说明书"})
        engine.pass_qa(3)
        qa_service.inspect("srs", "test-project-qa-flow-001", 3, "passed")

        engine.advance_step(4)
        engine.complete_step(4, artifacts={"designs": "各种设计文档"})

        engine.fail_qa(4, reason="设计有缺陷")
        qa_service.rollback("task-004", "test-project-qa-flow-001", 4,
                            reason="设计有缺陷", suggestions=["请修改"])

        engine.complete_step(4, artifacts={"designs": "修正后的设计文档"})
        engine.pass_qa(4)
        qa_service.inspect("design", "test-project-qa-flow-001", 4, "passed")

        status = engine.get_current_status()
        assert status["current_step"] == 4
        assert status["qa_records_count"] == 4


class TestAgentRoleIntegration:
    """Agent角色集成测试"""

    def test_all_named_roles_defined(self):
        service = AgentRoleService()
        roles = service.get_all_roles()
        assert len(roles) == 9

        role_names = {r["role_name"] for r in roles}
        expected = {"haimei", "houxing", "houwang", "houfa", "houda",
                    "houfu", "hougui", "hourong", "houhua"}
        assert role_names == expected

    def test_workflow_executor_to_role_mapping(self):
        service = AgentRoleService()
        steps = get_default_steps()

        for step in steps:
            if step.executor_role is None:
                continue
            role = service.get_role_by_name(step.executor_role)
            assert role is not None, f"Step {step.step_number}: role '{step.executor_role}' not found"

    def test_qa_role_has_correct_type(self):
        service = AgentRoleService()
        qa_role = service.get_qa_role()
        assert qa_role["role_name"] == "hourong"
        assert qa_role["role_type"] == "qa"

    def test_swarm_managers_are_houfa_and_houda(self):
        service = AgentRoleService()
        managers = service.get_swarm_managers()
        assert len(managers) == 2
        manager_names = {m["role_name"] for m in managers}
        assert manager_names == {"houfa", "houda"}

    def test_security_role_is_houhua(self):
        service = AgentRoleService()
        security = service.get_security_role()
        assert security["role_name"] == "houhua"
        assert security["role_type"] == "security_officer"


class TestConcurrentProjects:
    """并发项目测试"""

    def test_multiple_projects_independent_workflow(self):
        project_a = WorkflowEngine(project_id="project-a")
        project_b = WorkflowEngine(project_id="project-b")
        project_c = WorkflowEngine(project_id="project-c")

        project_a.advance_step(2)
        project_a.complete_step(2)
        project_a.pass_qa(2)
        project_a.advance_step(3)

        project_b.advance_step(2)
        project_b.complete_step(2)
        project_b.pass_qa(2)
        project_b.advance_step(3)
        project_b.complete_step(3)
        project_b.pass_qa(3)
        project_b.advance_step(4)
        project_b.complete_step(4)
        project_b.pass_qa(4)
        project_b.advance_step(5)

        project_c.advance_step(2)
        project_c.complete_step(2)

        assert project_a.current_step == 3
        assert project_b.current_step == 5
        assert project_c._step_states[2].status == "qa_review"

    def test_concurrent_projects_preserved_artifacts_isolation(self):
        engine_a = WorkflowEngine(project_id="proj-a")
        engine_b = WorkflowEngine(project_id="proj-b")

        engine_a.advance_step(2)
        engine_a.complete_step(2, artifacts={"goal": "目标A"})
        engine_a.pass_qa(2)

        engine_b.advance_step(2)
        engine_b.complete_step(2, artifacts={"goal": "目标B"})
        engine_b.pass_qa(2)

        preserved_a = engine_a.get_preserved_artifacts()
        preserved_b = engine_b.get_preserved_artifacts()

        assert preserved_a["step_2"]["goal"] == "目标A"
        assert preserved_b["step_2"]["goal"] == "目标B"

    def test_swarm_services_per_project_isolation(self):
        service_a = SwarmService()
        service_b = SwarmService()

        swarm_a = service_a.create_swarm("proj-a", "项目A蜂群", "code_writing", 9, "houfa")
        swarm_b = service_b.create_swarm("proj-b", "项目B蜂群", "code_writing", 9, "houfa")

        service_a.add_member(swarm_a["id"], "claude_code", "claude-1")
        service_b.add_member(swarm_b["id"], "opencode", "opencode-1")

        tasks_a = [{"task_id": "a-1", "name": "任务A1"}]
        service_a.dispatch_tasks(swarm_a["id"], tasks_a)

        tasks_b = [{"task_id": "b-1", "name": "任务B1"}]
        service_b.dispatch_tasks(swarm_b["id"], tasks_b)

        progress_a = service_a.get_progress(swarm_a["id"])
        progress_b = service_b.get_progress(swarm_b["id"])

        assert progress_a["total_tasks"] == 1
        assert progress_b["total_tasks"] == 1


class TestFullQATraceability:
    """QA检验记录完整可追溯性测试"""

    def test_qa_records_contain_all_required_fields(self):
        engine = WorkflowEngine(project_id="test-project-trace-001")

        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "目标"})
        record = engine.pass_qa(2, qa_agent_id="hourong")

        assert record.id is not None
        assert record.project_id == "test-project-trace-001"
        assert record.workflow_step_id == 2
        assert record.qa_agent_id == "hourong"
        assert record.status == "passed"
        assert record.inspected_at is not None

    def test_failed_qa_record_has_problem_details(self):
        engine = WorkflowEngine(project_id="test-project-trace-002")

        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)

        engine.advance_step(3)
        engine.complete_step(3, artifacts={"srs": "不完整"})
        record = engine.fail_qa(3, reason="缺少验收标准", suggestions=["补充验收标准"])

        assert record.status == "failed"
        assert record.problem_details == "缺少验收标准"
        assert record.fix_suggestions is not None

    def test_qa_records_count_matches_qa_steps(self):
        engine = WorkflowEngine(project_id="test-project-trace-003")

        for step_num in range(2, 11):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={f"step_{step_num}": "done"})
            if step_num in engine.QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)

        status = engine.get_current_status()
        qa_steps_done = {s for s in range(2, 11) if s in engine.QA_REQUIRED_STEPS}
        assert status["qa_records_count"] == len(qa_steps_done)

    def test_qa_record_after_iteration(self):
        engine = WorkflowEngine(project_id="test-project-trace-004")

        engine.advance_step(2)
        engine.complete_step(2)
        engine.pass_qa(2)

        engine.advance_step(3)
        engine.complete_step(3)
        engine.pass_qa(3)
        engine.advance_step(4)
        engine.complete_step(4)
        engine.pass_qa(4)

        engine.user_dissatisfied("不满意")

        pre_iteration_count = engine.get_current_status()["qa_records_count"]
        assert pre_iteration_count == 3  # steps 2, 3, 4 passed QA

        engine.advance_step(3)
        engine.complete_step(3, artifacts={"srs": "新SRS"})
        engine.pass_qa(3)

        post_iteration_count = engine.get_current_status()["qa_records_count"]
        assert post_iteration_count == 4  # 原有3条 + 新1条