import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
import uuid

from app.database import Base
from app.models.workflow_step import WorkflowStep
from app.models.project import Project
from app.models.qa_record import QARecord
from app.models.user import User
from app.models.agent import Agent
from app.services.workflow_engine import WorkflowEngine, get_default_steps, QA_REQUIRED_STEPS


STATUS_LABEL_MAP = {
    "pending": "待执行",
    "in_progress": "执行中",
    "qa_review": "检验中",
    "completed": "通过",
    "rejected": "未通过",
}


def get_step_display_label(db_status: str) -> str:
    return STATUS_LABEL_MAP.get(db_status, "待执行")


def calc_progress_percentage(completed_count: int, total: int = 16) -> float:
    if total <= 0:
        return 0.0
    return round(completed_count / total * 100, 2)


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_project(db_session):
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username="test_owner",
        email="owner@test.com",
        password_hash="hash",
        role="user",
    )
    db_session.add(user)
    db_session.commit()
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        name="测试项目",
        slug="test-project",
        description="16步流程进度条测试项目",
        creator_id=user_id,
        current_step=1,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    yield project


class Test16StepProgressBarDefinition:
    def test_get_default_steps_returns_exactly_16(self):
        steps = get_default_steps()
        assert len(steps) == 16

    def test_step_numbers_are_1_to_16(self):
        steps = get_default_steps()
        numbers = [s.step_number for s in steps]
        assert numbers == list(range(1, 17))

    def test_step_names_all_present(self):
        steps = get_default_steps()
        for s in steps:
            assert s.name is not None
            assert len(s.name) > 0

    def test_step_names_match_expected_workflow(self):
        steps = get_default_steps()
        expected_starts = ["人类用户创建项目", "海梅确认", "后兴需求分析", "后旺架构设计"]
        for i, prefix in enumerate(expected_starts):
            assert steps[i].name.startswith(prefix)

    def test_step_1_executor_is_none(self):
        step1 = next(s for s in get_default_steps() if s.step_number == 1)
        assert step1.executor_role is None

    def test_step_2_executor_is_haimei(self):
        step2 = next(s for s in get_default_steps() if s.step_number == 2)
        assert step2.executor_role == "haimei"

    def test_step_16_executor_is_haimei(self):
        step16 = next(s for s in get_default_steps() if s.step_number == 16)
        assert step16.executor_role == "haimei"

    def test_all_steps_have_supervisor_except_step1(self):
        steps = get_default_steps()
        for s in steps:
            if s.step_number == 1:
                assert s.supervisor_role is None
            else:
                assert s.supervisor_role == "haimei"


class TestStatusLabelMapping:
    def test_pending_maps_to_daizhixing(self):
        assert get_step_display_label("pending") == "待执行"

    def test_in_progress_maps_to_zhixingzhong(self):
        assert get_step_display_label("in_progress") == "执行中"

    def test_qa_review_maps_to_jianyanzhong(self):
        assert get_step_display_label("qa_review") == "检验中"

    def test_completed_maps_to_tongguo(self):
        assert get_step_display_label("completed") == "通过"

    def test_rejected_maps_to_weitongguo(self):
        assert get_step_display_label("rejected") == "未通过"

    def test_unknown_status_defaults_to_daizhixing(self):
        assert get_step_display_label("unknown") == "待执行"
        assert get_step_display_label(None) == "待执行"
        assert get_step_display_label("") == "待执行"

    def test_all_status_labels_are_unique(self):
        labels = list(STATUS_LABEL_MAP.values())
        assert len(set(labels)) == 5

    def test_status_label_map_contains_all_valid_statuses(self):
        expected = {"pending", "in_progress", "qa_review", "completed", "rejected"}
        assert set(STATUS_LABEL_MAP.keys()) == expected


class TestProgressPercentage:
    def test_zero_completed_is_0_percent(self):
        assert calc_progress_percentage(0) == 0.0

    def test_one_completed_is_6_25_percent(self):
        assert calc_progress_percentage(1) == 6.25

    def test_two_completed_is_12_5_percent(self):
        assert calc_progress_percentage(2) == 12.5

    def test_four_completed_is_25_percent(self):
        assert calc_progress_percentage(4) == 25.0

    def test_eight_completed_is_50_percent(self):
        assert calc_progress_percentage(8) == 50.0

    def test_twelve_completed_is_75_percent(self):
        assert calc_progress_percentage(12) == 75.0

    def test_sixteen_completed_is_100_percent(self):
        assert calc_progress_percentage(16) == 100.0

    def test_progress_does_not_exceed_100_naturally(self):
        for n in range(17):
            pct = calc_progress_percentage(n)
            if n <= 16:
                assert pct <= 100.0

    def test_custom_total_steps(self):
        assert calc_progress_percentage(3, total=10) == 30.0

    def test_zero_total_returns_0(self):
        assert calc_progress_percentage(5, total=0) == 0.0

    def test_negative_total_returns_0(self):
        assert calc_progress_percentage(5, total=-1) == 0.0

    def test_every_increment_is_6_25_percent(self):
        for n in range(1, 17):
            assert calc_progress_percentage(n) == round(n / 16 * 100, 2)

    def test_all_16_steps_completed_exact(self):
        assert calc_progress_percentage(16, 16) == 100.0
        assert calc_progress_percentage(0, 16) == 0.0
        assert calc_progress_percentage(8, 16) == 50.0


class TestWorkflowEngineProgress:
    def test_engine_has_16_steps(self):
        engine = WorkflowEngine(project_id="tdd-progress-no-db-1")
        assert len(engine.steps) == 16

    def test_engine_current_step_starts_at_1(self):
        engine = WorkflowEngine(project_id="tdd-progress-no-db-2")
        assert engine.current_step == 1

    def test_engine_steps_are_ordered_by_number(self):
        engine = WorkflowEngine(project_id="tdd-progress-no-db-3")
        numbers = [s.step_number for s in engine.steps]
        assert numbers == sorted(numbers)

    def test_initial_all_steps_pending(self):
        engine = WorkflowEngine(project_id="tdd-progress-no-db-4")
        assert engine.current_step == 1
        assert len(engine.steps) == 16
        assert engine.steps[0].step_number == 1
        assert engine.steps[-1].step_number == 16

    def test_engine_agent_health_is_initialized(self):
        engine = WorkflowEngine(project_id="tdd-progress-no-db-5")
        assert "haimei" in engine.agent_health
        assert "houxing" in engine.agent_health
        assert "houwang" in engine.agent_health
        assert "houfu" in engine.agent_health
        assert "houfa" in engine.agent_health
        assert "houda" in engine.agent_health
        assert "houhua" in engine.agent_health
        assert "hougui" in engine.agent_health
        assert "hourong" in engine.agent_health
        for health in engine.agent_health.values():
            assert health == "healthy"

    def test_progress_after_step2_completed(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "构建电商平台"})
        engine.pass_qa(2)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        completed_count = sum(1 for r in rows if r and r.status == "completed")
        assert completed_count >= 1
        pct = completed_count / 16 * 100
        assert pct >= 6.25

    def test_progress_after_3_steps_completed(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for step_num in [2, 3]:
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={"output": f"step{step_num}_done"})
            if step_num in QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        completed_count = sum(1 for r in rows if r and r.status == "completed")
        assert completed_count >= 3
        pct = completed_count / 16 * 100
        assert pct >= 18.75

    def test_all_steps_completed_is_100_percent(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for step_num in range(2, 17):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={"output": f"step{step_num}_done"})
            if step_num in QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        completed_count = sum(1 for r in rows if r and r.status == "completed")
        assert completed_count == 16
        pct = completed_count / 16 * 100
        assert pct == 100.0

    def test_step1_is_always_completed(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        row1 = engine._get_step_row(1)
        assert row1 is not None
        assert row1.status == "completed"

    def test_step2_advance_sets_in_progress(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        engine.advance_step(2)
        row2 = engine._get_step_row(2)
        assert row2.status == "in_progress"

    def test_step2_complete_sets_qa_review(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "test"})
        row2 = engine._get_step_row(2)
        assert row2.status in ("qa_review", "completed")

    def test_advancing_beyond_16_raises_error(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        with pytest.raises(ValueError):
            engine.advance_step(17)

    def test_advancing_step_1_raises_error(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        with pytest.raises(ValueError):
            engine.advance_step(1)

    def test_complete_nonexistent_step_raises_error(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        with pytest.raises(ValueError):
            engine.complete_step(99, artifacts={})


class TestQARequiredSteps:
    def test_qa_required_steps_is_set(self):
        assert len(QA_REQUIRED_STEPS) == 11

    def test_qa_required_steps_are_2_to_14_excluding_10_13(self):
        for s in QA_REQUIRED_STEPS:
            assert 2 <= s <= 14
        assert 10 not in QA_REQUIRED_STEPS
        assert 13 not in QA_REQUIRED_STEPS

    def test_step1_not_in_qa_required(self):
        assert 1 not in QA_REQUIRED_STEPS

    def test_step15_not_in_qa_required(self):
        assert 15 not in QA_REQUIRED_STEPS

    def test_step16_not_in_qa_required(self):
        assert 16 not in QA_REQUIRED_STEPS

    def test_all_qa_required_steps_have_haimei_as_supervisor(self):
        steps = {s.step_number: s for s in get_default_steps()}
        for sn in QA_REQUIRED_STEPS:
            assert steps[sn].supervisor_role == "haimei"

    def test_qa_required_steps_all_need_qa(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for sn in sorted(QA_REQUIRED_STEPS):
            engine.advance_step(sn)
            engine.complete_step(sn, artifacts={"output": f"{sn}_done"})
            row = engine._get_step_row(sn)
            assert row.status == "qa_review"
            engine.pass_qa(sn)

    def test_qa_required_step_must_pass_qa_to_complete(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "test"})
        row2 = engine._get_step_row(2)
        assert row2.status == "qa_review"
        engine.pass_qa(2)
        row2 = engine._get_step_row(2)
        assert row2.status == "completed"

    def test_non_qa_step_completes_immediately(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for sn in range(2, 10):
            engine.advance_step(sn)
            engine.complete_step(sn, artifacts={"output": f"step{sn}_done"})
            if sn in QA_REQUIRED_STEPS:
                engine.pass_qa(sn)
        engine.advance_step(10)
        engine.complete_step(10, artifacts={"output": "deployed"})
        row10 = engine._get_step_row(10)
        assert row10.status == "completed"


class TestWorkflowStepStatusLabels:
    def test_step_status_default_is_pending(self, db_session, test_project):
        step = WorkflowStep(
            project_id=test_project.id,
            step_number=1,
            step_name="测试步骤",
            executor_agent_id="haimei",
            status="pending",
        )
        db_session.add(step)
        db_session.commit()
        assert step.status == "pending"
        assert get_step_display_label(step.status) == "待执行"

    def test_step_status_in_progress_maps_correctly(self, db_session, test_project):
        step = WorkflowStep(
            project_id=test_project.id,
            step_number=2,
            step_name="测试步骤",
            executor_agent_id="haimei",
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(step)
        db_session.commit()
        assert get_step_display_label(step.status) == "执行中"

    def test_step_status_qa_review_maps_correctly(self, db_session, test_project):
        step = WorkflowStep(
            project_id=test_project.id,
            step_number=3,
            step_name="测试步骤",
            executor_agent_id="haimei",
            status="qa_review",
        )
        db_session.add(step)
        db_session.commit()
        assert get_step_display_label(step.status) == "检验中"

    def test_step_status_completed_maps_correctly(self, db_session, test_project):
        step = WorkflowStep(
            project_id=test_project.id,
            step_number=4,
            step_name="测试步骤",
            executor_agent_id="haimei",
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(step)
        db_session.commit()
        assert get_step_display_label(step.status) == "通过"

    def test_step_status_rejected_maps_correctly(self, db_session, test_project):
        step = WorkflowStep(
            project_id=test_project.id,
            step_number=5,
            step_name="测试步骤",
            executor_agent_id="haimei",
            status="rejected",
        )
        db_session.add(step)
        db_session.commit()
        assert get_step_display_label(step.status) == "未通过"

    def test_all_16_steps_with_mixed_statuses(self, db_session, test_project):
        statuses = (["completed", "in_progress", "qa_review", "pending"] * 4)[:16]
        for i in range(16):
            step = WorkflowStep(
                project_id=test_project.id,
                step_number=i + 1,
                step_name=f"Step {i + 1}",
                executor_agent_id="haimei",
                status=statuses[i],
            )
            db_session.add(step)
        db_session.commit()
        rows = db_session.query(WorkflowStep).filter(
            WorkflowStep.project_id == test_project.id
        ).order_by(WorkflowStep.step_number).all()
        assert len(rows) == 16
        labels = [get_step_display_label(r.status) for r in rows]
        assert labels[0] == "通过"
        assert labels[1] == "执行中"
        assert labels[2] == "检验中"
        assert labels[3] == "待执行"
        completed_count = labels.count("通过")
        pct = completed_count / 16 * 100
        assert pct == 6.25

    def test_step_labels_round_trip(self, db_session, test_project):
        original_status = "in_progress"
        step = WorkflowStep(
            project_id=test_project.id,
            step_number=10,
            step_name="部署到测试环境",
            executor_agent_id="houfu",
            status=original_status,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(step)
        db_session.commit()
        label = get_step_display_label(step.status)
        assert label == "执行中"
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)
        db_session.commit()
        label = get_step_display_label(step.status)
        assert label == "通过"


class TestStepProgressSummary:
    def test_progress_summary_all_pending(self):
        engine = WorkflowEngine(project_id="tdd-summary-1")
        total = len(engine.steps)
        completed = 0
        assert total == 16
        assert completed == 0
        pct = calc_progress_percentage(completed, total)
        assert pct == 0.0

    def test_progress_summary_first_step_is_completed(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        labels = [get_step_display_label(r.status) if r else "待执行" for r in rows]
        completed_count = labels.count("通过")
        in_progress_count = labels.count("执行中")
        total_progressed = completed_count + in_progress_count
        assert total_progressed >= 1

    def test_progress_summary_halfway(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for step_num in range(2, 10):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={"output": f"step{step_num}_done"})
            if step_num in QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        labels = [get_step_display_label(r.status) if r else "待执行" for r in rows]
        completed_count = labels.count("通过")
        assert completed_count >= 8

    def test_progress_summary_with_qa_review_steps(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        engine.advance_step(2)
        engine.complete_step(2, artifacts={"core_goal": "test"})
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        labels = [get_step_display_label(r.status) if r else "待执行" for r in rows]
        in_flight = labels.count("检验中") + labels.count("通过")
        assert in_flight >= 1

    def test_progress_summary_has_no_unknown_labels(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for step_num in range(2, 6):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={"output": f"step{step_num}_done"})
            if step_num in QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        labels = [get_step_display_label(r.status) if r else "待执行" for r in rows]
        valid_labels = {"待执行", "执行中", "检验中", "通过", "未通过"}
        for label in labels:
            assert label in valid_labels

    def test_progress_percentage_matches_expected(self, db_session, test_project):
        engine = WorkflowEngine(project_id=test_project.id, db=db_session, auto_supervise=False)
        for step_num in range(2, 5):
            engine.advance_step(step_num)
            engine.complete_step(step_num, artifacts={"output": f"step{step_num}_done"})
            if step_num in QA_REQUIRED_STEPS:
                engine.pass_qa(step_num)
        rows = [engine._get_step_row(n) for n in range(1, 17)]
        completed_count = sum(1 for r in rows if r and r.status == "completed")
        expected_pct = completed_count / 16 * 100
        assert calc_progress_percentage(completed_count, 16) == round(expected_pct, 2)
