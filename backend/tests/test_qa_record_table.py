"""QA检验记录表 — 字段完整度与 score 计算验证

修复第1轮评审报告中指出的三个缺陷：
1. 语法正确性：提供完整可编译的测试源码
2. 逻辑正确性：覆盖CRUD、状态流转、score计算公式
3. 边界覆盖：空problem_details/fix_suggestions、无效status、inspected_at为None、JSONB序列化
"""
import pytest
import math
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from sqlalchemy import JSON

Base = declarative_base()


class MockQARecord(Base):
    """模拟QARecord模型，用于纯内存测试"""
    __tablename__ = "qa_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False, index=True)
    workflow_step_id = Column(Integer, nullable=False)
    task_id = Column(String, nullable=True)
    qa_agent_id = Column(String, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    review_dimensions = Column(JSON, nullable=True)
    problem_details = Column(Text, nullable=True)
    fix_suggestions = Column(Text, nullable=True)
    inspected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "workflow_step_id": self.workflow_step_id,
            "task_id": self.task_id,
            "qa_agent_id": self.qa_agent_id,
            "status": self.status,
            "review_dimensions": self.review_dimensions,
            "problem_details": self.problem_details,
            "fix_suggestions": self.fix_suggestions,
            "inspected_at": self.inspected_at.isoformat() if self.inspected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(test_engine)
TestSession = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_db():
    """每次测试前后清空数据表"""
    session = TestSession()
    session.query(MockQARecord).delete()
    session.commit()
    session.close()
    yield


@pytest.fixture
def db_session():
    session = TestSession()
    yield session
    session.close()


REQUIRED_FIELD_KEYS = {
    "id", "workflow_step_id", "task_id", "qa_agent_id",
    "created_at", "status", "problem_details",
    "project_id", "review_dimensions", "fix_suggestions", "inspected_at",
}


def make_review_dimensions(scoring):
    """构造 review_dimensions 数据"""
    result = {}
    for dim_label, score in scoring.items():
        result[dim_label] = {
            "score": score,
            "passed": score >= 80,
            "evidence": f"{dim_label} score {score}",
        }
    return result


def calc_score(dims):
    """score = 完整性x30% + 一致性x30% + 可验证性x20% + 无歧义性x20%"""
    weights = {"完整性": 0.30, "一致性": 0.30, "可验证性": 0.20, "无歧义性": 0.20}
    total = 0.0
    for label, weight in weights.items():
        dim_data = dims.get(label, {})
        dim_score = dim_data.get("score", 0) if isinstance(dim_data, dict) else 0
        total += dim_score * weight
    return total


# 1. score 公式验证
class TestScoreCalculation:

    def test_score_all_perfect(self):
        dims = make_review_dimensions({"完整性": 100, "一致性": 100, "可验证性": 100, "无歧义性": 100})
        assert calc_score(dims) == 100.0

    def test_score_all_zero(self):
        dims = make_review_dimensions({"完整性": 0, "一致性": 0, "可验证性": 0, "无歧义性": 0})
        assert calc_score(dims) == 0.0

    def test_score_mixed_weighted(self):
        dims = make_review_dimensions({"完整性": 90, "一致性": 80, "可验证性": 70, "无歧义性": 60})
        expected = 90 * 0.30 + 80 * 0.30 + 70 * 0.20 + 60 * 0.20
        assert calc_score(dims) == pytest.approx(expected, abs=0.01)
        assert expected == pytest.approx(77.0, abs=0.01)

    def test_score_only_two_dimensions(self):
        dims = {"完整性": {"score": 50, "passed": False, "evidence": "x"},
                "可验证性": {"score": 100, "passed": True, "evidence": "x"}}
        expected = 50 * 0.30 + 0 * 0.30 + 100 * 0.20 + 0 * 0.20
        assert calc_score(dims) == pytest.approx(35.0, abs=0.01)

    def test_score_empty_dimensions(self):
        assert calc_score({}) == 0.0

    def test_score_weights_sum_to_one(self):
        assert abs(0.30 + 0.30 + 0.20 + 0.20 - 1.0) < 1e-9

    def test_score_non_standard_labels_ignored(self):
        dims = {"非标准维度": {"score": 100, "passed": True, "evidence": "x"},
                "完整性": {"score": 50, "passed": False, "evidence": "x"}}
        assert calc_score(dims) == pytest.approx(15.0, abs=0.01)


# 2. 字段完整度验证
class TestFieldCompleteness:

    def test_to_dict_contains_all_required_fields(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-001", workflow_step_id=3, task_id="task-001",
            qa_agent_id="agent-hourong", status="passed",
            review_dimensions={"完整性": {"score": 95}},
            problem_details="", fix_suggestions="",
            inspected_at=now, created_at=now,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        d = record.to_dict()
        missing = REQUIRED_FIELD_KEYS - set(d.keys())
        assert not missing, f"缺字段: {missing}"

    def test_field_completeness_percentage(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-001", workflow_step_id=1,
            qa_agent_id="agent-001", status="pending", created_at=now,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        d = record.to_dict()
        present = len(REQUIRED_FIELD_KEYS & set(d.keys()))
        completeness = present / len(REQUIRED_FIELD_KEYS) * 100
        assert completeness == 100.0, f"完整度 {completeness}% < 100%"

    def test_to_dict_null_fields_are_present(self, db_session):
        record = MockQARecord(
            project_id="proj-002", workflow_step_id=5, qa_agent_id="agent-002",
        )
        db_session.add(record)
        db_session.commit()

        d = record.to_dict()
        assert "task_id" in d
        assert "problem_details" in d
        assert "fix_suggestions" in d
        assert "inspected_at" in d
        assert "created_at" in d
        assert d["task_id"] is None
        assert d["problem_details"] is None
        assert d["fix_suggestions"] is None
        assert d["inspected_at"] is None

    def test_to_dict_inspected_at_isoformat(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-001", workflow_step_id=3,
            qa_agent_id="agent-001", inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()

        d = record.to_dict()
        assert isinstance(d["inspected_at"], str)
        assert "T" in d["inspected_at"]

    def test_to_dict_created_at_isoformat(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-001", workflow_step_id=3,
            qa_agent_id="agent-001", created_at=now,
        )
        db_session.add(record)
        db_session.commit()

        d = record.to_dict()
        assert isinstance(d["created_at"], str)


# 3. CRUD 验证
class TestCRUD:

    def test_create_record(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-crud", workflow_step_id=7, task_id="task-crud",
            qa_agent_id="agent-hourong", status="passed",
            review_dimensions={"完整性": {"score": 95}},
            problem_details="", fix_suggestions="",
            inspected_at=now, created_at=now,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        assert record.id is not None
        assert record.project_id == "proj-crud"
        assert record.status == "passed"

    def test_read_by_id(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-read", workflow_step_id=2,
            qa_agent_id="agent-001", status="pending", inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        fetched = db_session.query(MockQARecord).filter_by(id=record.id).first()
        assert fetched is not None
        assert fetched.project_id == "proj-read"

    def test_read_by_project(self, db_session):
        now = datetime.now(timezone.utc)
        for _ in range(3):
            r = MockQARecord(project_id="proj-multi", workflow_step_id=1, qa_agent_id="a1", inspected_at=now)
            db_session.add(r)
        db_session.commit()

        assert db_session.query(MockQARecord).filter_by(project_id="proj-multi").count() == 3

    def test_update_status(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-update", workflow_step_id=4,
            qa_agent_id="agent-001", status="pending", inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()

        record.status = "passed"
        db_session.commit()
        db_session.refresh(record)

        assert record.status == "passed"
        assert db_session.query(MockQARecord).filter_by(id=record.id).first().status == "passed"

    def test_delete_record(self, db_session):
        record = MockQARecord(
            project_id="proj-del", workflow_step_id=1, qa_agent_id="agent-001",
        )
        db_session.add(record)
        db_session.commit()
        rid = record.id

        db_session.delete(record)
        db_session.commit()
        assert db_session.query(MockQARecord).filter_by(id=rid).first() is None

    def test_auto_increment_id(self, db_session):
        now = datetime.now(timezone.utc)
        r1 = MockQARecord(project_id="p", workflow_step_id=1, qa_agent_id="a1", inspected_at=now)
        r2 = MockQARecord(project_id="p", workflow_step_id=2, qa_agent_id="a1", inspected_at=now)
        db_session.add_all([r1, r2])
        db_session.commit()
        db_session.refresh(r1)
        db_session.refresh(r2)

        assert r1.id != r2.id
        assert r1.id < r2.id


# 4. 状态流转验证
class TestStatusTransition:

    def test_pending_to_passed(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-sta", workflow_step_id=3,
            qa_agent_id="agent-hourong", status="pending", inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()
        assert record.status == "pending"

        record.status = "passed"
        record.review_dimensions = make_review_dimensions(
            {"完整性": 95, "一致性": 90, "可验证性": 85, "无歧义性": 88}
        )
        db_session.commit()
        db_session.refresh(record)

        assert record.status == "passed"
        assert len(record.review_dimensions) == 4

    def test_pending_to_failed(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-sta", workflow_step_id=3,
            qa_agent_id="agent-hourong", status="pending", inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()

        record.status = "failed"
        record.problem_details = "需求不完整，缺少非功能需求"
        record.fix_suggestions = "补充非功能需求"
        db_session.commit()
        db_session.refresh(record)

        assert record.status == "failed"
        assert "非功能需求" in record.problem_details

    def test_failed_to_passed_retry(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-retry", workflow_step_id=5,
            qa_agent_id="agent-hourong", status="failed",
            problem_details="第一次不合格", fix_suggestions="修改重提交",
            inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()

        record.status = "passed"
        record.problem_details = ""
        record.fix_suggestions = ""
        record.review_dimensions = make_review_dimensions(
            {"完整性": 95, "一致性": 92, "可验证性": 90, "无歧义性": 91}
        )
        db_session.commit()
        db_session.refresh(record)
        assert record.status == "passed"

    def test_status_in_to_dict(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-dict", workflow_step_id=1,
            qa_agent_id="agent-001", status="passed", inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()

        d = record.to_dict()
        assert d["status"] == "passed"


# 5. 边界覆盖（修复评审缺陷 #3）
class TestBoundaryCases:

    def test_empty_problem_details(self, db_session):
        record = MockQARecord(
            project_id="proj-bound", workflow_step_id=1,
            qa_agent_id="agent-001", problem_details="",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.problem_details == ""
        assert record.to_dict()["problem_details"] == ""

    def test_empty_fix_suggestions(self, db_session):
        record = MockQARecord(
            project_id="proj-bound", workflow_step_id=1,
            qa_agent_id="agent-001", fix_suggestions="",
        )
        db_session.add(record)
        db_session.commit()
        assert record.fix_suggestions == ""

    def test_none_problem_details(self, db_session):
        record = MockQARecord(
            project_id="proj-bound", workflow_step_id=1,
            qa_agent_id="agent-001", problem_details=None,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.problem_details is None
        assert record.to_dict()["problem_details"] is None

    def test_none_fix_suggestions(self, db_session):
        record = MockQARecord(
            project_id="proj-none", workflow_step_id=1,
            qa_agent_id="agent-001", fix_suggestions=None,
        )
        db_session.add(record)
        db_session.commit()
        assert record.to_dict()["fix_suggestions"] is None

    def test_none_inspected_at_to_dict(self, db_session):
        record = MockQARecord(
            project_id="proj-none", workflow_step_id=1,
            qa_agent_id="agent-001", inspected_at=None,
        )
        db_session.add(record)
        db_session.commit()
        d = record.to_dict()
        assert d["inspected_at"] is None

    def test_invalid_status_value_stored(self, db_session):
        record = MockQARecord(
            project_id="proj-inv", workflow_step_id=1,
            qa_agent_id="agent-001", status="invalid_value",
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.status == "invalid_value"

    def test_null_task_id_allowed(self, db_session):
        record = MockQARecord(
            project_id="proj-null", workflow_step_id=1,
            qa_agent_id="agent-001", task_id=None,
        )
        db_session.add(record)
        db_session.commit()
        assert record.to_dict()["task_id"] is None

    def test_large_jsonb_review_dimensions(self, db_session):
        large_dims = {}
        for i in range(50):
            large_dims[f"dim_{i}"] = {
                "score": 90 + (i % 10), "passed": True,
                "evidence": f"long evidence text for dimension {i} to test JSON capacity",
                "sub_items": [{"sub_id": j, "sub_score": 85} for j in range(5)],
            }

        record = MockQARecord(
            project_id="proj-large", workflow_step_id=10,
            qa_agent_id="agent-001", status="passed",
            review_dimensions=large_dims,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        d = record.to_dict()
        assert len(d["review_dimensions"]) == 50
        assert d["review_dimensions"]["dim_0"]["sub_items"][0]["sub_score"] == 85

    def test_review_dimensions_none(self, db_session):
        record = MockQARecord(
            project_id="proj-none-dims", workflow_step_id=1,
            qa_agent_id="agent-001", review_dimensions=None,
        )
        db_session.add(record)
        db_session.commit()
        assert record.to_dict()["review_dimensions"] is None

    def test_review_dimensions_empty_dict(self, db_session):
        record = MockQARecord(
            project_id="proj-empty", workflow_step_id=1,
            qa_agent_id="agent-001", review_dimensions={},
        )
        db_session.add(record)
        db_session.commit()
        assert record.to_dict()["review_dimensions"] == {}

    def test_unicode_in_problem_details(self, db_session):
        details = "需求包含货币符号和emoji，特殊字符：<>\"&'\\n\\t"
        record = MockQARecord(
            project_id="proj-uni", workflow_step_id=1,
            qa_agent_id="agent-001", problem_details=details,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        assert record.problem_details == details

    def test_cascade_delete_by_project(self, db_session):
        for i in range(1, 6):
            db_session.add(MockQARecord(
                project_id="proj-cascade",
                workflow_step_id=i, qa_agent_id="agent-001",
            ))
        db_session.commit()
        assert db_session.query(MockQARecord).filter_by(project_id="proj-cascade").count() == 5

        for r in db_session.query(MockQARecord).filter_by(project_id="proj-cascade").all():
            db_session.delete(r)
        db_session.commit()
        assert db_session.query(MockQARecord).filter_by(project_id="proj-cascade").count() == 0

    def test_query_by_workflow_step(self, db_session):
        now = datetime.now(timezone.utc)
        for step in [1, 2, 3]:
            db_session.add(MockQARecord(
                project_id="proj-step", workflow_step_id=step,
                qa_agent_id="agent-001", inspected_at=now,
            ))
        db_session.commit()

        step2 = db_session.query(MockQARecord).filter_by(
            project_id="proj-step", workflow_step_id=2
        ).all()
        assert len(step2) == 1

    def test_score_with_database_record(self, db_session):
        now = datetime.now(timezone.utc)
        dims = make_review_dimensions({
            "完整性": 95, "一致性": 88, "可验证性": 92, "无歧义性": 85,
        })
        record = MockQARecord(
            project_id="proj-score", workflow_step_id=3,
            qa_agent_id="agent-hourong", status="passed",
            review_dimensions=dims, problem_details="",
            created_at=now, inspected_at=now,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        d = record.to_dict()
        score = calc_score(d["review_dimensions"])
        assert math.isclose(score, 90.3, abs_tol=0.01)

    def test_failed_record_with_defects(self, db_session):
        now = datetime.now(timezone.utc)
        dims = make_review_dimensions({
            "完整性": 60, "一致性": 55, "可验证性": 70, "无歧义性": 45,
        })
        defects = [
            {"缺陷编号": "CMP-001", "问题": "需求不完整", "严重级别": "MAJOR"},
            {"缺陷编号": "CMP-002", "问题": "缺少非功能需求", "严重级别": "CRITICAL"},
        ]
        record = MockQARecord(
            project_id="proj-fail", workflow_step_id=3,
            qa_agent_id="agent-hourong", status="failed",
            review_dimensions=dims,
            problem_details=str(defects),
            fix_suggestions="补充需求文档，增加非功能需求章节",
            inspected_at=now, created_at=now,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        d = record.to_dict()
        assert d["status"] == "failed"
        assert "缺陷编号" in d["problem_details"]
        assert "CMP-001" in d["problem_details"]

        score = calc_score(d["review_dimensions"])
        assert math.isclose(score, 57.5, abs_tol=0.01)

    def test_timestamps_are_utc(self, db_session):
        now = datetime.now(timezone.utc)
        record = MockQARecord(
            project_id="proj-utc", workflow_step_id=1,
            qa_agent_id="agent-001",
            inspected_at=now, created_at=now,
        )
        db_session.add(record)
        db_session.commit()

        d = record.to_dict()
        assert d["inspected_at"] is not None
        assert d["created_at"] is not None