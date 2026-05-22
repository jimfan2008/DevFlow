import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.agent import Agent
from app.models.hermes_skill import HermesSkill
from app.services.profile_scanner_service import profile_scanner
from app.services.gateway_health import check_agent_online

logger = logging.getLogger("devflow.profile_sync")


def _gateway_host() -> str:
    return os.environ.get("HERMES_GATEWAY_HOST", "localhost")


async def sync_profiles_to_db(db: Session) -> Dict[str, int]:
    profiles = await profile_scanner.get_all_profiles(force_refresh=True)
    created_count = 0
    updated_count = 0
    skills_created_count = 0

    for profile in profiles:
        existing = db.query(Agent).filter(Agent.name == profile.name).first()

        config_data = {
            "gateway_port": profile.gateway_port,
            "model_default": profile.model_default,
            "model_provider": profile.model_provider,
            "config_path": profile.config_path,
            "is_running": profile.is_running,
            "use_cli": profile.is_running and not profile.gateway_port,
        }
        if profile.personality:
            config_data["personality"] = profile.personality
        if profile.api_key:
            config_data["api_key"] = profile.api_key

        if profile.gateway_port:
            is_online = await check_agent_online(profile.gateway_port, profile.api_key)
            status = "online" if is_online else "offline"
        elif profile.is_running:
            status = "online"
            logger.info(f"Profile '{profile.name}' running=true, no port, using CLI mode -> status=online")
        else:
            status = "offline"

        if existing:
            existing.status = status
            existing.config = config_data
            if profile.gateway_port:
                existing.api_endpoint = f"http://{_gateway_host()}:{profile.gateway_port}"
            existing.last_heartbeat = datetime.now(timezone.utc) if status == "online" else existing.last_heartbeat
            updated_count += 1
            logger.info(f"Updated agent '{profile.name}': status={status}")
        else:
            agent = Agent(
                name=profile.name,
                agent_type="hermes",
                status=status,
                api_endpoint=f"http://{_gateway_host()}:{profile.gateway_port}" if profile.gateway_port else None,
                discovered_by="profile_scan",
                profile_path=profile.config_path,
                config=config_data,
            )
            if status == "online":
                agent.last_heartbeat = datetime.now(timezone.utc)
            db.add(agent)
            db.flush()
            created_count += 1

            skills_created = _ensure_hermes_skills(db, agent.id)
            skills_created_count += skills_created

    db.commit()
    return {
        "discovered": len(profiles),
        "created": created_count,
        "updated": updated_count,
        "skills_created": skills_created_count,
    }


def _ensure_hermes_skills(db: Session, hermes_agent_id: str) -> int:
    skill_types = ["discover_agent", "connect_agent", "assign_task", "receive_message"]
    created = 0
    for skill_type in skill_types:
        existing = db.query(HermesSkill).filter(
            HermesSkill.hermes_agent_id == hermes_agent_id,
            HermesSkill.skill_type == skill_type,
        ).first()
        if not existing:
            skill = HermesSkill(
                hermes_agent_id=hermes_agent_id,
                skill_type=skill_type,
                status="active",
                connection_status="disconnected",
            )
            db.add(skill)
            created += 1
    return created


async def update_agent_online_status(db: Session) -> Dict[str, int]:
    agents = db.query(Agent).filter(Agent.agent_type == "hermes").all()
    online_count = 0
    offline_count = 0

    for agent in agents:
        config = agent.config or {}
        port = config.get("gateway_port")
        api_key = config.get("api_key")
        use_cli = config.get("use_cli", False)
        if port:
            is_online = await check_agent_online(port, api_key)
            new_status = "online" if is_online else "offline"
        elif use_cli:
            new_status = "online"
        else:
            new_status = "offline"

        if agent.status != new_status:
            agent.status = new_status
            if new_status == "online":
                agent.last_heartbeat = datetime.now(timezone.utc)
                online_count += 1
            else:
                offline_count += 1

    db.commit()
    return {"online": online_count, "offline": offline_count}
