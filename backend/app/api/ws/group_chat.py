import json
import uuid
import re
import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws.auth import verify_token
from app.services.chat_store import chat_store
from app.services.gateway_client import GatewayClient

logger = logging.getLogger(__name__)

router = APIRouter()

_active_connections: Dict[str, List[WebSocket]] = {}


async def broadcast(group_id: str, message: dict):
    dead: List[WebSocket] = []
    for ws in _active_connections.get(group_id, []):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    if dead:
        _active_connections[group_id] = [
            ws for ws in _active_connections.get(group_id, [])
            if ws not in dead
        ]


def _get_project_context(group_id: str) -> dict:
    from app.database import SessionLocal
    from app.models.group import Group as GroupModel
    from app.models.project import Project

    db = SessionLocal()
    try:
        group = db.query(GroupModel).filter(GroupModel.id == group_id).first()
        if not group or not group.project_id:
            return {}
        project = db.query(Project).filter(Project.id == group.project_id).first()
        if not project:
            return {}
        return {
            "project_id": project.id,
            "project_name": project.name,
            "project_description": project.description or "",
            "core_goal": project.core_goal or "",
            "project_slug": project.slug if project.slug else project.id,
        }
    except Exception as e:
        logger.warning(f"Failed to get project context: {e}")
        return {}
    finally:
        db.close()


@router.websocket("/group-chat/{group_id}")
async def group_chat_ws(websocket: WebSocket, group_id: str,
                        token: str = Query(...)):
    await websocket.accept()

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        user = await verify_token(token, db)
        if not user:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return

        _active_connections.setdefault(group_id, []).append(websocket)

        group = chat_store.get_group(group_id)
        if not group:
            group = _sync_group_from_db(group_id)
        if not group:
            await websocket.send_json({"type": "error", "message": "Group not found"})
            await websocket.close()
            return

        await websocket.send_json({"type": "subscribed", "group_id": group_id})

        try:
            while True:
                data = await websocket.receive_text()
                payload = json.loads(data)
                action = payload.get("action", "")

                if action == "send_message":
                    content = payload.get("content", "")
                    if content.strip():
                        asyncio.create_task(
                            _handle_message(group_id, content, group)
                        )
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            conns = _active_connections.get(group_id, [])
            if websocket in conns:
                conns.remove(websocket)
    except Exception as e:
        logger.error(f"GroupChat WS error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        db.close()


def _sync_group_from_db(group_id: str) -> Optional[dict]:
    from app.database import SessionLocal
    from app.services.group_service import GroupService

    db = SessionLocal()
    try:
        service = GroupService(db)
        db_group = service.get_group(group_id)
        if not db_group:
            return None
        gdict = db_group.to_dict()
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
        return chat_store.get_group(group_id)
    except Exception as e:
        logger.error(f"Failed to sync group {group_id}: {e}")
        return None
    finally:
        db.close()


async def _handle_message(group_id: str, content: str, group: dict):
    user_message = chat_store.add_message(
        group_id=group_id,
        sender="user",
        role="user",
        content=content
    )

    await broadcast(group_id, {
        "type": "message_new",
        "message": user_message
    })

    if not group.get("members"):
        return

    members = list(group.get("members", []))
    mention_pattern = r'@(\w+)'
    mentions = re.findall(mention_pattern, content)
    member_names_lower = {m.lower(): m for m in members}
    mentioned_agents = [member_names_lower[m.lower()] for m in mentions if m.lower() in member_names_lower]

    target_agents = mentioned_agents if mentioned_agents else members
    if not target_agents:
        return

    history = []
    for msg in chat_store.get_messages(group_id, limit=10):
        history.append({"role": msg["role"], "content": msg["content"]})

    ctx = _get_project_context(group_id)
    if not ctx:
        ctx = {"project_id": "", "project_name": "", "project_description": "", "core_goal": "", "project_slug": ""}

    asyncio.create_task(
        _dispatch_agents(group_id, target_agents, content, history, members, ctx)
    )


async def _dispatch_agents(
    group_id: str,
    profile_names: list,
    message: str,
    history: list,
    group_members: list,
    project_ctx: dict,
):
    member_names_lower = {m.lower(): m for m in group_members}
    all_finalized: set = set()
    round_history = list(history)
    pending = list(profile_names)
    round_message = message
    max_rounds = 5

    for _round_num in range(max_rounds):
        if not pending:
            break

        current_speaker = None
        current_message_id = None
        round_responses: Dict[str, str] = {}

        for profile_name in pending:
            try:
                await broadcast(group_id, {
                    "type": "agent_status",
                    "profile_name": profile_name,
                    "status": "typing"
                })

                client = GatewayClient(profile_name=profile_name, timeout=1800)
                full_reply = []
                first_chunk = True

                async for chunk in client.chat_isolated(
                    messages=history + [{"role": "user", "content": round_message}],
                    **project_ctx,
                    agent_name=profile_name,
                    stream=True,
                    max_tokens=64000,
                ):
                    if first_chunk:
                        current_speaker = profile_name
                        current_message_id = str(uuid.uuid4())
                        await broadcast(group_id, {
                            "type": "message_start",
                            "group_id": group_id,
                            "message_id": current_message_id,
                            "profile_name": profile_name
                        })
                        first_chunk = False

                    if chunk.strip():
                        full_reply.append(chunk)
                        await broadcast(group_id, {
                            "type": "message_chunk",
                            "group_id": group_id,
                            "message_id": current_message_id,
                            "profile_name": profile_name,
                            "content": chunk
                        })

                response = "".join(full_reply).strip()
                round_responses[profile_name] = response

                if response:
                    chat_store.add_message(
                        group_id=group_id,
                        sender=profile_name,
                        role="assistant",
                        content=response,
                        metadata={"type": "discussion_response"}
                    )

                await broadcast(group_id, {
                    "type": "agent_status",
                    "profile_name": profile_name,
                    "status": "idle"
                })

            except Exception as e:
                logger.error(f"Agent {profile_name} error: {e}")
                await broadcast(group_id, {
                    "type": "agent_error",
                    "profile_name": profile_name,
                    "error": str(e)
                })
                await broadcast(group_id, {
                    "type": "agent_status",
                    "profile_name": profile_name,
                    "status": "idle"
                })

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
        round_message = "上轮讨论中有人提到了你，请直接回应他们的观点。回复尽量简洁有针对性。"

    for profile_name in profile_names:
        await broadcast(group_id, {
            "type": "message_complete",
            "group_id": group_id,
            "profile_name": profile_name
        })
