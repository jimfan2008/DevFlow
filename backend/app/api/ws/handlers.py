import re
import uuid
import asyncio
import logging
from typing import Dict

from app.api.ws.manager import manager
from app.services.coordinator import coordinator
from app.services.chat_store import chat_store

logger = logging.getLogger(__name__)


def _get_or_sync_group(group_id: str) -> Dict | None:
    """从 chat_store 获取群，不存在则从主数据库同步过来"""
    group = chat_store.get_group(group_id)
    if group:
        return group

    # 回退：从主数据库查找并同步到 chat_store
    try:
        from app.database import SessionLocal
        from app.services.group_service import GroupService
        db = SessionLocal()
        try:
            service = GroupService(db)
            db_group = service.get_group(group_id)
            if not db_group:
                return None
            # 使用 to_dict() 获取普通 Python 值（避免 SQLAlchemy Column 类型问题）
            gdict = db_group.to_dict()
            # 同步到 chat_store
            chat_store.create_group(
                group_id=str(gdict["id"]),
                name=str(gdict["name"]),
                description=str(gdict.get("description") or ""),
                members=list(gdict.get("members") or [])
            )
            host = gdict.get("host_agent")
            if host:
                chat_store.update_group(group_id, host_agent=str(host))
            mode = gdict.get("mode")
            if mode and str(mode) != "discussion":
                chat_store.update_group(group_id, mode=str(mode))
            logger.info(f"Synced group {group_id} from main DB to chat_store")
            return chat_store.get_group(group_id)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to sync group {group_id} from main DB: {e}")
    return None


async def handle_send_message(group_id: str, content: str, sender_id: str):
    """处理发送消息"""
    group = _get_or_sync_group(group_id)
    if not group:
        await manager.send_to_client(sender_id, {
            "type": "error",
            "message": "Group not found"
        })
        return

    user_message = chat_store.add_message(
        group_id=group_id,
        sender="user",
        role="user",
        content=content
    )

    await manager.broadcast_to_group(group_id, {
        "type": "message_new",
        "message": user_message
    })

    if not group["members"]:
        return

    if group["mode"] == "meeting":
        return

    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, content)
    mentioned_agents = [m for m in mentions if m in group["members"]]

    target_agents = mentioned_agents if mentioned_agents else group["members"]
    if not target_agents:
        return

    history = []
    for msg in chat_store.get_messages(group_id, limit=10):
        history.append({"role": msg["role"], "content": msg["content"]})

    asyncio.create_task(dispatch_to_agents(group_id, target_agents, content, history))


async def dispatch_to_agents(
    group_id: str,
    profile_names: list,
    message: str,
    history: list
):
    """分发消息给 agents"""

    def progress_callback(profile_name: str, status: str):
        try:
            asyncio.create_task(
                manager.broadcast_to_group(group_id, {
                    "type": "agent_status",
                    "profile_name": profile_name,
                    "status": status
                })
            )
        except Exception as e:
            logger.warning(f"progress_callback error: {e}")

    agent_responses: Dict[str, str] = {}
    current_speaker = None
    current_message_id = None

    async for result in coordinator.discussion_mode(
        profile_names, message, history, progress_callback
    ):
        if "error" in result:
            await manager.broadcast_to_group(group_id, {
                "type": "agent_error",
                "profile_name": result["profile"],
                "error": result["error"]
            })
        else:
            profile = result["profile"]
            content = result.get("content", "")

            if profile != current_speaker:
                if current_speaker and current_speaker in agent_responses and agent_responses[current_speaker]:
                    _save_agent_message(group_id, current_speaker, agent_responses[current_speaker])

                current_speaker = profile
                current_message_id = str(uuid.uuid4())
                await manager.broadcast_to_group(group_id, {
                    "type": "message_start",
                    "group_id": group_id,
                    "message_id": current_message_id,
                    "profile_name": profile
                })

                if profile not in agent_responses:
                    agent_responses[profile] = ""
                else:
                    agent_responses[profile] = ""

            agent_responses[profile] += content

            await manager.broadcast_to_group(group_id, {
                "type": "message_chunk",
                "group_id": group_id,
                "message_id": current_message_id,
                "profile_name": profile,
                "content": content
            })

    if current_speaker and current_speaker in agent_responses and agent_responses[current_speaker]:
        _save_agent_message(group_id, current_speaker, agent_responses[current_speaker])

    for profile_name in profile_names:
        await manager.broadcast_to_group(group_id, {
            "type": "agent_status",
            "profile_name": profile_name,
            "status": "idle"
        })


def _save_agent_message(group_id: str, profile_name: str, content: str):
    """保存 agent 的完整发言到数据库"""
    if not content.strip():
        return
    try:
        chat_store.add_message(
            group_id=group_id,
            sender=profile_name,
            role="assistant",
            content=content,
            metadata={"type": "discussion_response"}
        )
    except Exception as e:
        logger.error(f"Error saving agent message for {profile_name}: {e}")
