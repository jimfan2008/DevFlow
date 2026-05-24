from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.config import settings

from app.services.hermes.hermes_api_client import HermesAPIClient
from app.services.hermes.hermes_chat import HermesChatService
from app.services.hermes.hermes_session import HermesSessionManager
from app.services.hermes.hermes_discovery import HermesDiscoveryService
from app.services.hermes.hermes_config import HermesConfigReader
from app.services.hermes.hermes_health import HermesHealthChecker
from app.services.hermes.types import SSEEvent, HermesAPIError

logger = logging.getLogger("devflow.hermes.router")
router = APIRouter(prefix="/hermes", tags=["hermes"], redirect_slashes=False)


_api_client: Optional[HermesAPIClient] = None
_health_checker: Optional[HermesHealthChecker] = None
_running_tasks: Dict[str, asyncio.Task] = {}


def _get_api_client() -> HermesAPIClient:
    global _api_client
    if _api_client is None:
        _api_client = HermesAPIClient(
            base_url=settings.HERMES_API_BASE,
            api_key=settings.HERMES_API_KEY,
            model=settings.HERMES_MODEL,
        )
    return _api_client


def _get_health_checker() -> HermesHealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HermesHealthChecker(
            api_client=_get_api_client(),
            interval=settings.HERMES_HEALTH_INTERVAL,
        )
    return _health_checker


class ChatStreamRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    profile_name: str = "default"


class CreateSessionRequest(BaseModel):
    profile_name: str = "default"
    model_id: str = "hermes-agent"
    display_name: Optional[str] = None


class RenameSessionRequest(BaseModel):
    display_name: str


@router.post("/chat/stream")
async def chat_stream(
    data: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api = _get_api_client()
    chat_svc = HermesChatService(api, db, show_thinking=settings.HERMES_SHOW_THINKING)
    session_mgr = HermesSessionManager(db)

    session_id = data.session_id
    if not session_id:
        session = session_mgr.create_session(
            user_id=current_user.id,
            profile_name=data.profile_name,
            model_id=data.model or settings.HERMES_MODEL,
        )
        session_id = session.id

    session = session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    history_msgs = session_mgr.get_messages(session_id)
    history = session_mgr.build_openai_messages(history_msgs, "")
    history.append({"role": "user", "content": data.message})

    session_mgr.add_message(session_id=session_id, role="user", content=data.message)

    async def event_generator():
        full_content = ""
        full_thinking = ""
        tool_calls = []
        try:
            async for event in chat_svc.stream_chat(
                session_id=session_id,
                message=data.message,
                model=data.model,
                profile_name=data.profile_name,
                history=history[:-1],
            ):
                if event.event == "content" and isinstance(event.data, dict):
                    full_content += event.data.get("content", "")
                elif event.event == "thinking" and isinstance(event.data, dict):
                    full_thinking += event.data.get("content", "")
                elif event.event == "tool_call" and isinstance(event.data, dict):
                    tool_calls.append(event.data)
                elif event.event == "done" and isinstance(event.data, dict):
                    full_content = event.data.get("content", full_content)
                    full_thinking = event.data.get("thinking_content", full_thinking)
                    tool_calls = event.data.get("tool_calls", tool_calls)
                yield event.encode()
        finally:
            try:
                session_mgr.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_content,
                    thinking_content=full_thinking if settings.HERMES_SHOW_THINKING else None,
                    tool_calls=tool_calls if tool_calls else None,
                    model=data.model or settings.HERMES_MODEL,
                )
            except Exception as e:
                logger.error(f"Failed to save assistant message: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/cancel")
async def cancel_chat(data: dict, current_user: User = Depends(get_current_user)):
    session_id = data.get("session_id", "")
    task = _running_tasks.pop(session_id, None)
    if task and not task.done():
        task.cancel()
        return {"code": 0, "message": "cancelled"}
    return {"code": 0, "message": "no running task"}


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mgr = HermesSessionManager(db)
    sessions = mgr.list_sessions(current_user.id, limit=limit)
    return {"code": 0, "data": [_session_to_dict(s) for s in sessions]}


@router.post("/sessions")
async def create_session(
    data: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mgr = HermesSessionManager(db)
    session = mgr.create_session(
        user_id=current_user.id,
        profile_name=data.profile_name,
        model_id=data.model_id,
        display_name=data.display_name,
    )
    return {"code": 0, "data": _session_to_dict(session)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mgr = HermesSessionManager(db)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = mgr.get_messages(session_id)
    return {"code": 0, "data": {"session": _session_to_dict(session), "messages": [_msg_to_dict(m) for m in messages]}}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mgr = HermesSessionManager(db)
    ok = mgr.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"code": 0, "message": "deleted"}


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    data: RenameSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mgr = HermesSessionManager(db)
    session = mgr.rename_session(session_id, data.display_name)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"code": 0, "data": _session_to_dict(session)}


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mgr = HermesSessionManager(db)
    messages = mgr.get_messages(session_id, limit=limit, offset=offset)
    return {"code": 0, "data": [_msg_to_dict(m) for m in messages]}


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    api = _get_api_client()
    try:
        models = await api.list_models()
        return {"code": 0, "data": [{"id": m.id, "provider": m.provider, "is_available": m.is_available} for m in models]}
    except HermesAPIError as e:
        return {"code": 1, "message": str(e), "data": []}


@router.get("/profiles")
async def list_profiles(current_user: User = Depends(get_current_user)):
    reader = HermesConfigReader()
    profiles = reader.scan_profiles()
    return {"code": 0, "data": [{"name": p.name, "path": p.path, "is_active": p.is_active, "has_config": p.has_config} for p in profiles]}


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    checker = _get_health_checker()
    return {"code": 0, "data": {"status": checker.status, "diagnostic": checker.get_diagnostic_info()}}


@router.get("/diagnose")
async def diagnose(current_user: User = Depends(get_current_user)):
    discovery = HermesDiscoveryService()
    result = discovery.discover()
    return {"code": 0, "data": {
        "hermes_home": result.hermes_home,
        "config_found": result.config_found,
        "api_server": {"reachable": result.api_server_info.reachable, "base_url": result.api_server_info.base_url, "model": result.api_server_info.model, "latency_ms": result.api_server_info.latency_ms},
        "connection_mode": result.connection_mode,
        "runtime_type": result.runtime_type,
        "steps": [{"step": s.step, "success": s.success, "detail": s.detail, "duration_ms": s.duration_ms} for s in result.diagnostic_steps],
    }}


@router.get("/health")
async def health_check():
    api = _get_api_client()
    ok = await api.health_check()
    return {"status": "ok" if ok else "unhealthy"}


def _session_to_dict(s) -> dict:
    return {
        "id": s.id, "user_id": s.user_id, "profile_name": s.profile_name,
        "model_id": s.model_id, "display_name": s.display_name,
        "message_count": s.message_count, "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _msg_to_dict(m) -> dict:
    tool_calls = None
    if m.tool_calls:
        try:
            tool_calls = json.loads(m.tool_calls)
        except Exception:
            tool_calls = m.tool_calls
    return {
        "id": m.id, "session_id": m.session_id, "role": m.role,
        "content": m.content, "thinking_content": m.thinking_content,
        "tool_calls": tool_calls, "model": m.model,
        "is_streaming": m.is_streaming, "is_interrupted": m.is_interrupted,
        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
    }
