import json
import uuid
import asyncio
import re
import logging
from datetime import datetime
from typing import Dict, Set, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.coordinator import coordinator
from app.services.gateway_client import GatewayClient
from app.services.chat_store import chat_store

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.group_subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        for group_id in self.group_subscriptions:
            self.group_subscriptions[group_id].discard(client_id)

    def subscribe_to_group(self, client_id: str, group_id: str):
        if group_id not in self.group_subscriptions:
            self.group_subscriptions[group_id] = set()
        self.group_subscriptions[group_id].add(client_id)

    def unsubscribe_from_group(self, client_id: str, group_id: str):
        if group_id in self.group_subscriptions:
            self.group_subscriptions[group_id].discard(client_id)

    async def send_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            ws = self.active_connections[client_id]
            await ws.send_json(message)

    async def broadcast_to_group(self, group_id: str, message: dict):
        if group_id in self.group_subscriptions:
            for client_id in self.group_subscriptions[group_id]:
                await self.send_to_client(client_id, message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "subscribe":
                group_id = message.get("group_id")
                if group_id:
                    manager.subscribe_to_group(client_id, group_id)
                    await manager.send_to_client(client_id, {
                        "type": "subscribed",
                        "group_id": group_id
                    })

            elif msg_type == "unsubscribe":
                group_id = message.get("group_id")
                if group_id:
                    manager.unsubscribe_from_group(client_id, group_id)

            elif msg_type == "send_message":
                group_id = message.get("group_id")
                content = message.get("content")

                if group_id and content:
                    await handle_send_message(group_id, content, client_id)

            elif msg_type == "start_meeting":
                group_id = message.get("group_id")
                topic = message.get("topic")
                host_agent = message.get("host_agent")
                meeting_type = message.get("meeting_type", "tech_solution")
                duration_minutes = message.get("duration_minutes", 45)
                pre_materials = message.get("pre_materials")
                rules = message.get("rules")

                if group_id and topic and host_agent:
                    logger.info(f"Received start_meeting: group={group_id}, topic={topic}")
                    asyncio.create_task(
                        handle_start_meeting(
                            group_id,
                            topic,
                            host_agent,
                            client_id,
                            meeting_type=meeting_type,
                            duration_minutes=duration_minutes,
                            pre_materials=pre_materials,
                            rules=rules
                        )
                    )

            elif msg_type == "stop_meeting":
                group_id = message.get("group_id")
                if group_id:
                    await handle_stop_meeting(group_id, client_id)

            elif msg_type == "meeting_intervention":
                group_id = message.get("group_id")
                content = message.get("content")
                if group_id and content:
                    asyncio.create_task(
                        handle_meeting_intervention(group_id, content, client_id)
                    )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)


async def handle_send_message(group_id: str, content: str, sender_id: str):
    """处理发送消息"""
    group = chat_store.get_group(group_id)
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


async def handle_meeting_intervention(group_id: str, content: str, sender_id: str):
    """处理用户在会议中的干预"""
    group = chat_store.get_group(group_id)
    if not group or group["mode"] != "meeting":
        await manager.send_to_client(sender_id, {
            "type": "error",
            "message": "No active meeting in this group"
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

    meeting = coordinator.get_meeting_state(group_id)
    if not meeting or not meeting.is_active:
        return

    logger.info(f"Processing meeting intervention in group {group_id}: {content[:50]}...")

    current_speaker = None
    current_message_id = None

    def progress_callback(profile_name: str, status: str):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                manager.broadcast_to_group(group_id, {
                    "type": "agent_status",
                    "group_id": group_id,
                    "profile_name": profile_name,
                    "status": status
                })
            )
        except Exception as e:
            logger.warning(f"progress_callback error: {e}")

    try:
        async for result in coordinator.handle_intervention(
            group_id, content, progress_callback
        ):
            event = result.get("event", "")
            profile = result.get("profile", "")
            result_content = result.get("content", "")
            data = result.get("data", "")

            if event == "speaking":
                if profile != current_speaker:
                    if current_message_id and current_speaker:
                        await manager.broadcast_to_group(group_id, {
                            "type": "message_complete",
                            "group_id": group_id,
                            "message_id": current_message_id,
                            "profile_name": current_speaker
                        })

                    current_speaker = profile
                    current_message_id = str(uuid.uuid4())
                    await manager.broadcast_to_group(group_id, {
                        "type": "message_start",
                        "group_id": group_id,
                        "message_id": current_message_id,
                        "profile_name": profile
                    })

                await manager.broadcast_to_group(group_id, {
                    "type": "message_chunk",
                    "group_id": group_id,
                    "message_id": current_message_id,
                    "profile_name": profile,
                    "content": result_content
                })

            elif event == "agenda_updated":
                await manager.broadcast_to_group(group_id, {
                    "type": "meeting_agenda",
                    "group_id": group_id,
                    "agenda": json.loads(data) if data else []
                })

        if current_message_id and current_speaker:
            await manager.broadcast_to_group(group_id, {
                "type": "message_complete",
                "group_id": group_id,
                "message_id": current_message_id,
                "profile_name": current_speaker
            })

    except Exception as e:
        logger.error(f"Meeting intervention error in group {group_id}: {e}", exc_info=True)
        await manager.broadcast_to_group(group_id, {
            "type": "agent_error",
            "group_id": group_id,
            "profile_name": meeting.host_agent if meeting else "",
            "error": str(e)
        })


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


async def handle_start_meeting(
    group_id: str,
    topic: str,
    host_agent: str,
    sender_id: str,
    meeting_type: str = "tech_solution",
    duration_minutes: int = 45,
    pre_materials: Optional[str] = None,
    rules: Optional[list] = None
):
    """处理开始会议"""
    logger.info(f"Starting meeting: group={group_id}, topic={topic}, host={host_agent}")
    group = chat_store.get_group(group_id)
    if not group:
        await manager.send_to_client(sender_id, {
            "type": "error",
            "message": "Group not found"
        })
        return

    if host_agent not in group["members"]:
        await manager.send_to_client(sender_id, {
            "type": "error",
            "message": f"Host agent '{host_agent}' is not a member of this group"
        })
        return

    if len(group["members"]) < 1:
        await manager.send_to_client(sender_id, {
            "type": "error",
            "message": "Group has no members"
        })
        return

    chat_store.update_group(group_id, mode="meeting", host_agent=host_agent)

    await manager.broadcast_to_group(group_id, {
        "type": "meeting_started",
        "group_id": group_id,
        "topic": topic,
        "host_agent": host_agent,
        "participants": group["members"],
        "meeting_type": meeting_type,
        "duration_minutes": duration_minutes
    })

    system_msg = chat_store.add_message(
        group_id=group_id,
        sender="system",
        role="system",
        content=f"会议开始 | 议题：{topic} | 主持人：{host_agent}",
        metadata={"type": "meeting_start", "topic": topic, "host_agent": host_agent}
    )

    await manager.broadcast_to_group(group_id, {
        "type": "message_new",
        "message": system_msg
    })

    def progress_callback(profile_name: str, status: str):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                manager.broadcast_to_group(group_id, {
                    "type": "agent_status",
                    "group_id": group_id,
                    "profile_name": profile_name,
                    "status": status
                })
            )
        except Exception as e:
            logger.warning(f"progress_callback error: {e}")

    current_message_id = None
    current_speaker = None
    meeting_start_time = datetime.now()

    try:
        async for result in coordinator.meeting_mode(
            group_id,
            group["members"],
            host_agent,
            topic,
            meeting_type=meeting_type,
            duration_minutes=duration_minutes,
            pre_materials=pre_materials,
            rules=rules,
            progress_callback=progress_callback
        ):
            event = result.get("event", "")
            profile = result.get("profile", "")
            content = result.get("content", "")
            data = result.get("data", "")

            if event == "phase":
                await manager.broadcast_to_group(group_id, {
                    "type": "meeting_phase",
                    "group_id": group_id,
                    "phase": data,
                    "description": content
                })

            elif event == "agenda_ready":
                await manager.broadcast_to_group(group_id, {
                    "type": "meeting_agenda",
                    "group_id": group_id,
                    "agenda": json.loads(data) if data else []
                })

            elif event == "agenda_item_start":
                await manager.broadcast_to_group(group_id, {
                    "type": "meeting_agenda_item",
                    "group_id": group_id,
                    "data": json.loads(data) if data else {},
                    "description": content
                })

            elif event == "grant_speak":
                await manager.broadcast_to_group(group_id, {
                    "type": "meeting_grant_speak",
                    "group_id": group_id,
                    "speaker": data,
                    "description": content
                })

            elif event == "speaking":
                if profile != current_speaker:
                    if current_message_id and current_speaker:
                        await manager.broadcast_to_group(group_id, {
                            "type": "message_complete",
                            "group_id": group_id,
                            "message_id": current_message_id,
                            "profile_name": current_speaker
                        })

                    current_speaker = profile
                    current_message_id = str(uuid.uuid4())
                    await manager.broadcast_to_group(group_id, {
                        "type": "message_start",
                        "group_id": group_id,
                        "message_id": current_message_id,
                        "profile_name": profile
                    })

                await manager.broadcast_to_group(group_id, {
                    "type": "message_chunk",
                    "group_id": group_id,
                    "message_id": current_message_id,
                    "profile_name": profile,
                    "content": content
                })

            elif event == "meeting_complete":
                if current_message_id and current_speaker:
                    await manager.broadcast_to_group(group_id, {
                        "type": "message_complete",
                        "group_id": group_id,
                        "message_id": current_message_id,
                        "profile_name": current_speaker
                    })

                await manager.broadcast_to_group(group_id, {
                    "type": "meeting_minutes",
                    "group_id": group_id,
                    "minutes": data
                })

        if current_message_id and current_speaker:
            await manager.broadcast_to_group(group_id, {
                "type": "message_complete",
                "group_id": group_id,
                "message_id": current_message_id,
                "profile_name": current_speaker
            })

        meeting_state = coordinator.get_meeting_state(group_id)
        if meeting_state and meeting_state.meeting_minutes:
            chat_store.add_message(
                group_id=group_id,
                sender=host_agent,
                role="assistant",
                content=meeting_state.meeting_minutes,
                metadata={"type": "meeting_minutes"}
            )

        if meeting_state:
            for entry in meeting_state.conversation_history[:-1]:
                chat_store.add_message(
                    group_id=group_id,
                    sender=entry["speaker"],
                    role=entry["role"],
                    content=entry["content"],
                    metadata={"type": "meeting_speech"}
                )

            if meeting_state.decisions or meeting_state.todos or meeting_state.risks or meeting_state.open_issues:
                outcome = chat_store.save_meeting_outcome(
                    group_id=group_id,
                    meeting_topic=topic,
                    host_agent=host_agent,
                    started_at=meeting_start_time,
                    minutes=meeting_state.meeting_minutes,
                    decisions=meeting_state.decisions,
                    todos=meeting_state.todos,
                    risks=meeting_state.risks,
                    open_issues=meeting_state.open_issues
                )
                logger.info(f"Saved meeting outcome for group {group_id}: {len(meeting_state.todos)} todos, {len(meeting_state.decisions)} decisions")

                for todo in meeting_state.todos:
                    assignee = todo.get("assignee", "")
                    description = todo.get("description", "")
                    deadline = todo.get("deadline", "")
                    if assignee and description:
                        task = chat_store.create_task(
                            group_id=group_id,
                            assignee=assignee,
                            description=description,
                            deadline=deadline,
                            meeting_id=outcome["id"]
                        )
                        logger.info(f"Created task {task['id']} for {assignee}: {description}")

                        asyncio.create_task(
                            manager.broadcast_to_group(group_id, {
                                "type": "task_created",
                                "group_id": group_id,
                                "task": task
                            })
                        )

                asyncio.create_task(
                    manager.broadcast_to_group(group_id, {
                        "type": "meeting_outcome_saved",
                        "group_id": group_id,
                        "meeting_outcome": outcome
                    })
                )

        end_msg = chat_store.add_message(
            group_id=group_id,
            sender="system",
            role="system",
            content="会议结束",
            metadata={"type": "meeting_end"}
        )

        await manager.broadcast_to_group(group_id, {
            "type": "message_new",
            "message": end_msg
        })

        chat_store.update_group(group_id, mode="discussion", host_agent=None)

        await manager.broadcast_to_group(group_id, {
            "type": "meeting_stopped",
            "group_id": group_id
        })

        if meeting_state and meeting_state.todos:
            todo_list_text = "\n".join([
                f"- {t.get('description', '')} (责任人: {t.get('assignee', '')}, 截止: {t.get('deadline', '无')})"
                for t in meeting_state.todos
            ])
            task_announcement = (
                f"会议「{topic}」已结束，以下是会议决策中安排的待办任务，请各成员认领并执行：\n\n"
                f"{todo_list_text}\n\n"
                f"请各负责人确认任务并开始执行。"
            )

            task_msg = chat_store.add_message(
                group_id=group_id,
                sender="system",
                role="system",
                content=task_announcement,
                metadata={"type": "task_dispatch"}
            )

            await manager.broadcast_to_group(group_id, {
                "type": "message_new",
                "message": task_msg
            })

            history = []
            for msg in chat_store.get_messages(group_id, limit=10):
                history.append({"role": msg["role"], "content": msg["content"]})

            asyncio.create_task(
                dispatch_to_agents(group_id, group["members"], task_announcement, history)
            )

    except Exception as e:
        logger.error(f"Meeting error in group {group_id}: {e}", exc_info=True)
        await manager.broadcast_to_group(group_id, {
            "type": "agent_error",
            "group_id": group_id,
            "profile_name": host_agent,
            "error": str(e)
        })
        chat_store.update_group(group_id, mode="discussion", host_agent=None)
        await manager.broadcast_to_group(group_id, {
            "type": "meeting_stopped",
            "group_id": group_id
        })


async def handle_stop_meeting(group_id: str, sender_id: str):
    """处理停止会议"""
    group = chat_store.get_group(group_id)
    if not group:
        await manager.send_to_client(sender_id, {
            "type": "error",
            "message": "Group not found"
        })
        return

    coordinator.cancel_meeting(group_id)
    chat_store.update_group(group_id, mode="discussion", host_agent=None)

    end_msg = chat_store.add_message(
        group_id=group_id,
        sender="system",
        role="system",
        content="会议已被手动结束",
        metadata={"type": "meeting_cancelled"}
    )

    await manager.broadcast_to_group(group_id, {
        "type": "message_new",
        "message": end_msg
    })

    await manager.broadcast_to_group(group_id, {
        "type": "meeting_stopped",
        "group_id": group_id
    })