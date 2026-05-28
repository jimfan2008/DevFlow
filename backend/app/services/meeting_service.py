from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.group import Group, GroupMessage, MeetingOutcome, GroupTask
from app.models.agent import Agent
from app.models.enums import MeetingType, GroupMode

logger = logging.getLogger("devflow.meeting")

MEETING_TEMPLATES = {
    MeetingType.requirement_review.value: {
        "name": "需求评审",
        "agenda": [
            {"step": 1, "item": "需求文档逐条审查"},
            {"step": 2, "item": "模糊点和矛盾识别"},
            {"step": 3, "item": "验收标准确认"},
            {"step": 4, "item": "修改建议汇总"},
        ],
        "rules": {"host_decides_on_dispute": True, "require_consensus": False},
    },
    MeetingType.tech_solution.value: {
        "name": "技术方案评审",
        "agenda": [
            {"step": 1, "item": "架构方案介绍"},
            {"step": 2, "item": "技术选型论证"},
            {"step": 3, "item": "风险评估"},
            {"step": 4, "item": "方案决议"},
        ],
        "rules": {"host_decides_on_dispute": True, "require_consensus": False},
    },
    MeetingType.daily_standup.value: {
        "name": "每日站会",
        "agenda": [
            {"step": 1, "item": "昨日完成情况"},
            {"step": 2, "item": "今日计划"},
            {"step": 3, "item": "风险与阻碍"},
        ],
        "rules": {"host_decides_on_dispute": False, "time_limit_minutes": 15},
    },
    MeetingType.incident_postmortem.value: {
        "name": "故障复盘",
        "agenda": [
            {"step": 1, "item": "故障时间线还原"},
            {"step": 2, "item": "根因分析"},
            {"step": 3, "item": "改进措施制定"},
            {"step": 4, "item": "责任确认与待办"},
        ],
        "rules": {"host_decides_on_dispute": True, "require_consensus": True},
    },
}


class MeetingService:
    def __init__(self, db: Session):
        self.db = db

    def start_meeting(self, group_id: str, topic: str, host_agent_name: str,
                      meeting_type: str = "tech_solution",
                      pre_materials: List[str] = None,
                      rules: Dict = None) -> Group:
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise ValueError("Group not found")

        if group.mode == GroupMode.meeting.value:
            raise ValueError("MEETING_001: Meeting already in progress for this group")

        host_agent = self.db.query(Agent).filter(Agent.name == host_agent_name).first()
        if not host_agent or host_agent.status != "online":
            raise ValueError("MEETING_002: Host agent is not online")

        template = MEETING_TEMPLATES.get(meeting_type, MEETING_TEMPLATES["tech_solution"])

        group.mode = GroupMode.meeting.value
        group.host_agent = host_agent_name

        meeting_msg = GroupMessage(
            id=str(uuid.uuid4()),
            group_id=group_id,
            sender="system",
            role="system",
            content=f"会议启动: {topic} (类型: {template['name']}, 主持人: {host_agent_name})",
            is_streaming=False,
            msg_metadata={
                "meeting_type": meeting_type,
                "topic": topic,
                "host_agent": host_agent_name,
                "agenda": template["agenda"],
                "pre_materials": pre_materials or [],
                "rules": rules or template["rules"],
            },
        )
        self.db.add(meeting_msg)
        self.db.commit()
        self.db.refresh(group)
        return group

    def stop_meeting(self, group_id: str, minutes: str = "",
                     decisions: List[Dict] = None, todos: List[Dict] = None,
                     risks: List[Dict] = None, open_issues: List[Dict] = None) -> MeetingOutcome:
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            raise ValueError("Group not found")

        if group.mode != GroupMode.meeting.value:
            raise ValueError("No meeting in progress for this group")

        now = datetime.now(timezone.utc)
        start_msg = self.db.query(GroupMessage).filter(
            and_(
                GroupMessage.group_id == group_id,
                GroupMessage.role == "system",
                GroupMessage.content.like("会议启动:%"),
            )
        ).order_by(GroupMessage.timestamp.desc()).first()

        started_at = start_msg.timestamp if start_msg else now
        meeting_topic = ""
        meeting_type = "tech_solution"
        host_agent = group.host_agent or ""
        agenda = []

        if start_msg and start_msg.msg_metadata:
            meeting_topic = start_msg.msg_metadata.get("topic", "")
            meeting_type = start_msg.msg_metadata.get("meeting_type", "tech_solution")
            agenda = start_msg.msg_metadata.get("agenda", [])

        outcome = MeetingOutcome(
            id=str(uuid.uuid4()),
            group_id=group_id,
            meeting_topic=meeting_topic,
            meeting_type=meeting_type,
            host_agent=host_agent,
            agenda=agenda,
            started_at=started_at,
            ended_at=now,
            minutes=minutes,
            decisions=decisions or [],
            todos=todos or [],
            risks=risks or [],
            open_issues=open_issues or [],
        )
        self.db.add(outcome)
        self.db.flush()

        if todos:
            for todo_item in todos:
                task = GroupTask(
                    id=str(uuid.uuid4()),
                    group_id=group_id,
                    meeting_id=outcome.id,
                    assignee=todo_item.get("assignee"),
                    description=todo_item.get("description", ""),
                    deadline=todo_item.get("deadline"),
                    status="pending",
                )
                self.db.add(task)

        group.mode = GroupMode.discussion.value
        self.db.commit()
        self.db.refresh(outcome)
        return outcome

    def handle_intervention(self, group_id: str, content: str, sender: str) -> GroupMessage:
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group or group.mode != GroupMode.meeting.value:
            raise ValueError("No active meeting in this group")

        msg = GroupMessage(
            id=str(uuid.uuid4()),
            group_id=group_id,
            sender=sender,
            role="user",
            content=content,
            is_streaming=False,
            msg_metadata={"type": "intervention"},
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def handle_dispute(self, group_id: str, dispute_content: str) -> GroupMessage:
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group or group.mode != GroupMode.meeting.value:
            raise ValueError("No active meeting")

        template_type = "tech_solution"
        start_msg = self.db.query(GroupMessage).filter(
            and_(
                GroupMessage.group_id == group_id,
                GroupMessage.role == "system",
                GroupMessage.content.like("会议启动:%"),
            )
        ).order_by(GroupMessage.timestamp.desc()).first()
        if start_msg and start_msg.msg_metadata:
            template_type = start_msg.msg_metadata.get("meeting_type", "tech_solution")

        template = MEETING_TEMPLATES.get(template_type, {})
        host_decides = template.get("rules", {}).get("host_decides_on_dispute", True)

        if host_decides and group.host_agent:
            resolution = f"主持人 {group.host_agent} 对争议做出裁决: {dispute_content}"
        else:
            resolution = f"争议记录待讨论: {dispute_content}"

        msg = GroupMessage(
            id=str(uuid.uuid4()),
            group_id=group_id,
            sender="system",
            role="system",
            content=resolution,
            is_streaming=False,
            msg_metadata={"type": "dispute_resolution", "host_decides": host_decides},
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def handle_host_offline(self, group_id: str) -> GroupMessage:
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group or group.mode != GroupMode.meeting.value:
            return None

        msg = GroupMessage(
            id=str(uuid.uuid4()),
            group_id=group_id,
            sender="system",
            role="system",
            content=f"主持人 {group.host_agent} 已离线，会议暂停，等待主持人恢复或指定新主持人",
            is_streaming=False,
            msg_metadata={"type": "host_offline"},
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_meeting_template(self, meeting_type: str) -> Dict:
        return MEETING_TEMPLATES.get(meeting_type, MEETING_TEMPLATES["tech_solution"])

    def get_meeting_outcomes(self, group_id: str) -> List[MeetingOutcome]:
        return (
            self.db.query(MeetingOutcome)
            .filter(MeetingOutcome.group_id == group_id)
            .order_by(MeetingOutcome.ended_at.desc())
            .all()
        )
