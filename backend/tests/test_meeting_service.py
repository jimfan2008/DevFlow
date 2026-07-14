"""v4.0 Meeting Service Tests - 会议模式（SRS 3.3.3）"""
import pytest
import uuid
from datetime import datetime, timezone
from app.services.meeting_service import MeetingService, MEETING_TEMPLATES
from app.models.group import Group, GroupMessage, MeetingOutcome
from app.models.agent import Agent
from app.models.enums import MeetingType, GroupMode


class TestMeetingTemplates:
    """会议模板定义测试"""

    def test_all_meeting_types_have_templates(self):
        assert len(MEETING_TEMPLATES) == 4

    def test_meeting_types_match_enum(self):
        expected = {t.value for t in MeetingType}
        assert set(MEETING_TEMPLATES.keys()) == expected

    def test_requirement_review_has_agenda(self):
        tmpl = MEETING_TEMPLATES["requirement_review"]
        assert len(tmpl["agenda"]) >= 4
        assert tmpl["rules"]["host_decides_on_dispute"] is True

    def test_tech_solution_has_agenda(self):
        tmpl = MEETING_TEMPLATES["tech_solution"]
        assert len(tmpl["agenda"]) >= 4
        assert tmpl["rules"]["host_decides_on_dispute"] is True

    def test_daily_standup_has_time_limit(self):
        tmpl = MEETING_TEMPLATES["daily_standup"]
        assert tmpl["rules"]["time_limit_minutes"] == 15
        assert tmpl["rules"]["host_decides_on_dispute"] is False

    def test_incident_postmortem_requires_consensus(self):
        tmpl = MEETING_TEMPLATES["incident_postmortem"]
        assert tmpl["rules"]["require_consensus"] is True


class TestMeetingStart:
    """会议启动测试"""

    def test_start_meeting_success(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei", "houxing"],
                      mode="discussion", host_agent="haimei")
        db_session.add(group)
        agent = Agent(id=str(uuid.uuid4()), name="haimei", agent_type="hermes", status="online")
        db_session.add(agent)
        db_session.commit()

        svc = MeetingService(db_session)
        result = svc.start_meeting(
            group_id=group.id, topic="需求评审V1", host_agent_name="haimei",
            meeting_type="requirement_review",
        )
        assert result.mode == "meeting"
        assert result.host_agent == "haimei"

    def test_start_meeting_group_not_found(self, db_session):
        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="Group not found"):
            svc.start_meeting("nonexistent", "topic", "haimei")

    def test_start_meeting_already_in_progress(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        agent = Agent(id=str(uuid.uuid4()), name="haimei", agent_type="hermes", status="online")
        db_session.add(agent)
        db_session.commit()

        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="MEETING_001"):
            svc.start_meeting(group.id, "topic", "haimei")

    def test_start_meeting_host_offline(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="discussion")
        db_session.add(group)
        agent = Agent(id=str(uuid.uuid4()), name="haimei", agent_type="hermes", status="offline")
        db_session.add(agent)
        db_session.commit()

        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="MEETING_002"):
            svc.start_meeting(group.id, "topic", "haimei")

    def test_start_meeting_creates_system_message(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="discussion")
        db_session.add(group)
        agent = Agent(id=str(uuid.uuid4()), name="haimei", agent_type="hermes", status="online")
        db_session.add(agent)
        db_session.commit()

        svc = MeetingService(db_session)
        svc.start_meeting(group.id, "API设计评审", "haimei", meeting_type="tech_solution")

        msgs = db_session.query(GroupMessage).filter(
            GroupMessage.group_id == group.id
        ).all()
        assert len(msgs) == 1
        assert msgs[0].sender == "system"
        assert "API设计评审" in msgs[0].content

    def test_start_meeting_all_types(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="discussion")
        db_session.add(group)
        agent = Agent(id=str(uuid.uuid4()), name="haimei", agent_type="hermes", status="online")
        db_session.add(agent)
        db_session.commit()

        svc = MeetingService(db_session)
        for meeting_type in MeetingType:
            gid = str(uuid.uuid4())
            g = Group(id=gid, name="g", members=["haimei"], mode="discussion")
            db_session.add(g)
            db_session.commit()

            result = svc.start_meeting(gid, f"test-{meeting_type.value}", "haimei",
                                       meeting_type=meeting_type.value)
            assert result.mode == "meeting"
            db_session.query(Group).filter(Group.id == gid).update({"mode": "discussion"})
            db_session.commit()


class TestMeetingStop:
    """会议结束测试"""

    def test_stop_meeting_success(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        outcome = svc.stop_meeting(
            group_id=group.id, minutes="会议完成",
            decisions=[{"decision": "采用微服务架构"}],
            todos=[{"assignee": "houwang", "description": "输出架构文档"}],
        )
        assert outcome is not None
        assert outcome.minutes == "会议完成"
        assert len(outcome.decisions) == 1
        assert len(outcome.todos) == 1

        updated = db_session.query(Group).filter(Group.id == group.id).first()
        assert updated.mode == "discussion"

    def test_stop_meeting_no_active_meeting(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="discussion")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="No meeting in progress"):
            svc.stop_meeting(group.id)

    def test_stop_meeting_creates_meeting_outcome(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        outcome = svc.stop_meeting(
            group_id=group.id,
            minutes="评审通过",
            decisions=[{"decision": "使用PostgreSQL"}],
            todos=[],
            risks=[{"risk": "性能风险", "level": "high"}],
            open_issues=[{"issue": "缓存方案待定"}],
        )
        assert outcome.minutes == "评审通过"
        assert len(outcome.risks) == 1
        assert len(outcome.open_issues) == 1

    def test_stop_meeting_group_not_found(self, db_session):
        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="Group not found"):
            svc.stop_meeting("nonexistent")

    def test_stop_meeting_todos_create_group_tasks(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei", "houxing"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        outcome = svc.stop_meeting(
            group_id=group.id,
            todos=[
                {"assignee": "houxing", "description": "更新需求文档"},
                {"assignee": "houwang", "description": "画出架构图"},
            ],
        )
        assert len(outcome.todos) == 2

        from app.models.group import GroupTask
        tasks = db_session.query(GroupTask).filter(
            GroupTask.meeting_id == outcome.id
        ).all()
        assert len(tasks) == 2


class TestMeetingDispute:
    """会议争议处理测试"""

    def test_host_decides_dispute(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei", "houwang"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        result = svc.handle_dispute(group.id, "微服务 vs 单体架构争议")
        assert result is not None
        assert "主持人" in result.content
        assert "haimei" in result.content

    def test_dispute_no_active_meeting(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", mode="discussion")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="No active meeting"):
            svc.handle_dispute(group.id, "争议")

    def test_dispute_no_host_sets_consensus(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["houwang"],
                      mode="meeting", host_agent=None)
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        result = svc.handle_dispute(group.id, "技术选型争议")
        assert "争议记录" in result.content


class TestMeetingIntervention:
    """会议人工干预测试"""

    def test_user_intervention(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        msg = svc.handle_intervention(group.id, "请先讨论数据库选型", "user_001")
        assert msg.sender == "user_001"
        assert msg.msg_metadata.get("type") == "intervention"

    def test_intervention_no_active_meeting(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", mode="discussion")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        with pytest.raises(ValueError, match="No active meeting"):
            svc.handle_intervention(group.id, "干预", "user_001")


class TestMeetingHostOffline:
    """主持人离线处理测试"""

    def test_host_offline_pauses_meeting(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="meeting", host_agent="haimei")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        msg = svc.handle_host_offline(group.id)
        assert msg is not None
        assert "离线" in msg.content
        assert "暂停" in msg.content

    def test_host_offline_no_meeting_returns_none(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", mode="discussion")
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        result = svc.handle_host_offline(group.id)
        assert result is None


class TestMeetingOutcomes:
    """会议成果查询测试"""

    def test_get_meeting_outcomes_empty(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"])
        db_session.add(group)
        db_session.commit()

        svc = MeetingService(db_session)
        outcomes = svc.get_meeting_outcomes(group.id)
        assert outcomes == []

    def test_get_meeting_outcomes_with_records(self, db_session):
        group = Group(id=str(uuid.uuid4()), name="test-group", members=["haimei"],
                      mode="discussion")
        db_session.add(group)
        outcome1 = MeetingOutcome(
            id=str(uuid.uuid4()), group_id=group.id, meeting_topic="topic1",
            meeting_type="tech_solution", host_agent="haimei",
            agenda=[], started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc), minutes="m1",
            decisions=[], todos=[], risks=[], open_issues=[],
        )
        outcome2 = MeetingOutcome(
            id=str(uuid.uuid4()), group_id=group.id, meeting_topic="topic2",
            meeting_type="requirement_review", host_agent="haimei",
            agenda=[], started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc), minutes="m2",
            decisions=[], todos=[], risks=[], open_issues=[],
        )
        db_session.add_all([outcome1, outcome2])
        db_session.commit()

        svc = MeetingService(db_session)
        outcomes = svc.get_meeting_outcomes(group.id)
        assert len(outcomes) == 2

    def test_get_meeting_templates(self, db_session):
        svc = MeetingService(db_session)
        for meeting_type in MeetingType:
            tmpl = svc.get_meeting_template(meeting_type.value)
            assert tmpl is not None
            assert "name" in tmpl
            assert "agenda" in tmpl
            assert "rules" in tmpl

    def test_get_unknown_meeting_templates_fallback(self, db_session):
        svc = MeetingService(db_session)
        tmpl = svc.get_meeting_template("unknown_type")
        assert tmpl == MEETING_TEMPLATES["tech_solution"]
