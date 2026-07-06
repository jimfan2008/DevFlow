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
    member_names_lower = {m.lower(): m for m in group["members"]}
    mentioned_agents = [member_names_lower[m.lower()] for m in mentions if m.lower() in member_names_lower]

    target_agents = mentioned_agents if mentioned_agents else group["members"]
    if not target_agents:
        return

    history = []
    for msg in chat_store.get_messages(group_id, limit=10):
        history.append({"role": msg["role"], "content": msg["content"]})

    asyncio.create_task(dispatch_to_agents(group_id, target_agents, content, history, group["members"]))


async def dispatch_to_agents(
    group_id: str,
    profile_names: list,
    message: str,
    history: list,
    group_members: list
):
    """分发消息给 agents，支持多轮 agent 间 @ 互相交流"""

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

    member_names_lower = {m.lower(): m for m in group_members}
    all_finalized: set = set()         # agents that have already spoken
    round_history = list(history)      # grows with each round
    pending = list(profile_names)      # agents to speak in current round
    round_message = message
    max_rounds = 5

    for _round_num in range(max_rounds):
        if not pending:
            break

        current_speaker = None
        current_message_id = None
        round_responses: Dict[str, str] = {}

        async for result in coordinator.discussion_mode(
            pending, round_message, round_history, progress_callback
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
                    if current_speaker and current_speaker in round_responses and round_responses[current_speaker]:
                        _save_agent_message(group_id, current_speaker, round_responses[current_speaker])

                    current_speaker = profile
                    current_message_id = str(uuid.uuid4())
                    await manager.broadcast_to_group(group_id, {
                        "type": "message_start",
                        "group_id": group_id,
                        "message_id": current_message_id,
                        "profile_name": profile
                    })

                    if profile not in round_responses:
                        round_responses[profile] = ""
                    else:
                        round_responses[profile] = ""

                round_responses[profile] += content

                await manager.broadcast_to_group(group_id, {
                    "type": "message_chunk",
                    "group_id": group_id,
                    "message_id": current_message_id,
                    "profile_name": profile,
                    "content": content
                })

        if current_speaker and current_speaker in round_responses and round_responses[current_speaker]:
            _save_agent_message(group_id, current_speaker, round_responses[current_speaker])

        for p in round_responses:
            all_finalized.add(p)

        new_mentions = set()
        for profile, response in round_responses.items():
            if not response.strip():
                continue
            mentions = re.findall(r'@(\w+)', response)
            for m in mentions:
                if m.lower() in member_names_lower:
                    actual = member_names_lower[m.lower()]
                    if actual != profile and actual not in all_finalized:
                        new_mentions.add(actual)

        if not new_mentions:
            break

        context_lines = []
        for p in pending:
            r = round_responses.get(p, "")
            if r.strip():
                context_lines.append(f"{p}: {r}")
        if context_lines:
            round_history.append({"role": "assistant", "content": "\n\n".join(context_lines)})

        pending = list(new_mentions)
        round_message = f"上轮讨论中有人提到了你，请直接回应他们的观点。回复尽量简洁有针对性。"
        logger.info(f"Agent interaction round {_round_num + 2}: @mentions {new_mentions}")

    for profile_name in profile_names:
        await manager.broadcast_to_group(group_id, {
            "type": "message_complete",
            "group_id": group_id,
            "profile_name": profile_name
        })
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
