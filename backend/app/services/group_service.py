from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.group import Group, GroupMessage, MeetingOutcome, GroupTask


class GroupService:
    def __init__(self, db: Session):
        self.db = db

    def create_group(self, name: str, description: str = "", members: List[str] = None) -> Group:
        group = Group(
            name=name,
            description=description,
            members=members or [],
            mode="discussion"
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def get_group(self, group_id: str) -> Optional[Group]:
        return self.db.query(Group).filter(Group.id == group_id).first()

    def get_all_groups(self) -> List[Group]:
        return self.db.query(Group).order_by(Group.created_at.desc()).all()

    def update_group(self, group_id: str, **kwargs) -> Optional[Group]:
        group = self.get_group(group_id)
        if not group:
            return None
        for key, value in kwargs.items():
            if hasattr(group, key) and value is not None:
                setattr(group, key, value)
        self.db.commit()
        self.db.refresh(group)
        return group

    def delete_group(self, group_id: str) -> bool:
        group = self.get_group(group_id)
        if not group:
            return False
        self.db.delete(group)
        self.db.commit()
        return True

    def add_member(self, group_id: str, profile_name: str) -> Optional[Group]:
        group = self.get_group(group_id)
        if not group:
            return None
        if group.members is None:
            group.members = []
        if profile_name not in group.members:
            group.members.append(profile_name)
            self.db.commit()
            self.db.refresh(group)
        return group

    def remove_member(self, group_id: str, profile_name: str) -> Optional[Group]:
        group = self.get_group(group_id)
        if not group:
            return None
        if group.members and profile_name in group.members:
            group.members.remove(profile_name)
            self.db.commit()
            self.db.refresh(group)
        return group

    def add_message(
        self,
        group_id: str,
        sender: str,
        role: str,
        content: str,
        metadata: dict = None
    ) -> GroupMessage:
        message = GroupMessage(
            group_id=group_id,
            sender=sender,
            role=role,
            content=content,
            is_streaming=False,
            metadata=metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(self, group_id: str, limit: int = 100) -> List[GroupMessage]:
        return (
            self.db.query(GroupMessage)
            .filter(GroupMessage.group_id == group_id)
            .order_by(GroupMessage.timestamp.asc())
            .limit(limit)
            .all()
        )

    def save_meeting_outcome(
        self,
        group_id: str,
        meeting_topic: str,
        host_agent: str,
        started_at: datetime,
        ended_at: datetime,
        minutes: str = "",
        decisions: List[dict] = None,
        todos: List[dict] = None,
        risks: List[dict] = None,
        open_issues: List[dict] = None
    ) -> MeetingOutcome:
        outcome = MeetingOutcome(
            group_id=group_id,
            meeting_topic=meeting_topic,
            host_agent=host_agent,
            started_at=started_at,
            ended_at=ended_at,
            minutes=minutes,
            decisions=decisions or [],
            todos=todos or [],
            risks=risks or [],
            open_issues=open_issues or []
        )
        self.db.add(outcome)
        self.db.commit()
        self.db.refresh(outcome)
        return outcome

    def get_meeting_outcomes(self, group_id: str) -> List[MeetingOutcome]:
        return (
            self.db.query(MeetingOutcome)
            .filter(MeetingOutcome.group_id == group_id)
            .order_by(MeetingOutcome.ended_at.desc())
            .all()
        )

    def create_task(
        self,
        group_id: str,
        assignee: str,
        description: str,
        deadline: str = None,
        meeting_id: str = None
    ) -> GroupTask:
        task = GroupTask(
            group_id=group_id,
            meeting_id=meeting_id,
            assignee=assignee,
            description=description,
            deadline=deadline,
            status="pending"
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_pending_tasks(self, assignee: str = None) -> List[GroupTask]:
        query = self.db.query(GroupTask).filter(GroupTask.status != "completed")
        if assignee:
            query = query.filter(GroupTask.assignee == assignee)
        return query.order_by(GroupTask.created_at.desc()).all()

    def update_task_status(self, task_id: str, status: str, result: str = "") -> Optional[GroupTask]:
        task = self.db.query(GroupTask).filter(GroupTask.id == task_id).first()
        if not task:
            return None
        task.status = status
        task.result = result
        if status == "completed":
            task.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task
