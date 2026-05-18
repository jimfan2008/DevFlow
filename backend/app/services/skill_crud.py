from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.hermes_skill import HermesSkill
from app.models.agent import Agent


def get_skill(db: Session, skill_id: str) -> Optional[HermesSkill]:
    return db.query(HermesSkill).filter(HermesSkill.id == skill_id).first()


def get_skills_by_hermes_agent(db: Session, hermes_agent_id: str) -> List[HermesSkill]:
    return db.query(HermesSkill).filter(HermesSkill.hermes_agent_id == hermes_agent_id).all()


def get_skill_by_type(db: Session, hermes_agent_id: str, skill_type: str) -> Optional[HermesSkill]:
    return db.query(HermesSkill).filter(
        and_(
            HermesSkill.hermes_agent_id == hermes_agent_id,
            HermesSkill.skill_type == skill_type,
        )
    ).first()


def get_active_skills(db: Session, hermes_agent_id: str) -> List[HermesSkill]:
    return db.query(HermesSkill).filter(
        and_(
            HermesSkill.hermes_agent_id == hermes_agent_id,
            HermesSkill.status == "active",
        )
    ).all()


def create_skill(db: Session, hermes_agent_id: str, skill_type: str, **kwargs) -> HermesSkill:
    skill = HermesSkill(
        hermes_agent_id=hermes_agent_id,
        skill_type=skill_type,
        status=kwargs.get("status", "active"),
        config=kwargs.get("config", {}),
        coding_agent_id=kwargs.get("coding_agent_id"),
        task_id=kwargs.get("task_id"),
        connection_status=kwargs.get("connection_status", "disconnected"),
    )
    db.add(skill)
    db.flush()
    return skill


def update_skill(db: Session, skill_id: str, **kwargs) -> Optional[HermesSkill]:
    skill = get_skill(db, skill_id)
    if not skill:
        return None
    for key, value in kwargs.items():
        if hasattr(skill, key) and value is not None:
            setattr(skill, key, value)
    skill.updated_at = datetime.now(timezone.utc)
    db.flush()
    return skill


def update_skill_connection_status(db: Session, skill_id: str, connection_status: str) -> Optional[HermesSkill]:
    return update_skill(db, skill_id, connection_status=connection_status)


def update_skill_execution(db: Session, skill_id: str, stats: Dict[str, Any] = None) -> Optional[HermesSkill]:
    skill = get_skill(db, skill_id)
    if not skill:
        return None
    skill.last_executed_at = datetime.now(timezone.utc)
    if stats:
        current_stats = skill.execution_stats or {}
        current_stats.update(stats)
        skill.execution_stats = current_stats
    db.flush()
    return skill


def delete_skill(db: Session, skill_id: str) -> bool:
    skill = get_skill(db, skill_id)
    if not skill:
        return False
    db.delete(skill)
    db.flush()
    return True


def get_skill_execution_history(db: Session, skill_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    from app.models.agent_execution_log import AgentExecutionLog
    skill = get_skill(db, skill_id)
    if not skill:
        return []
    logs = db.query(AgentExecutionLog).filter(
        AgentExecutionLog.via_skill_type == skill.skill_type,
        AgentExecutionLog.agent_id == skill.hermes_agent_id,
    ).order_by(AgentExecutionLog.created_at.desc()).limit(limit).all()
    return [log.to_dict() for log in logs]


def ensure_four_skills(db: Session, hermes_agent_id: str) -> List[HermesSkill]:
    skill_types = ["discover_agent", "connect_agent", "assign_task", "receive_message"]
    skills = []
    for skill_type in skill_types:
        existing = get_skill_by_type(db, hermes_agent_id, skill_type)
        if not existing:
            skill = create_skill(db, hermes_agent_id, skill_type, connection_status="disconnected")
            skills.append(skill)
        else:
            skills.append(existing)
    db.flush()
    return skills
