import json
import uuid
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.ws.manager import manager
from app.api.ws.handlers import handle_send_message
from app.api.ws.meeting import handle_start_meeting, handle_stop_meeting, handle_meeting_intervention

logger = logging.getLogger(__name__)

router = APIRouter()


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
                            group_id, topic, host_agent, client_id,
                            meeting_type=meeting_type,
                            duration_minutes=duration_minutes,
                            pre_materials=pre_materials,
                            rules=rules,
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
