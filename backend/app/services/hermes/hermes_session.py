from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.hermes_session import HermesMessage, HermesSession

logger = logging.getLogger("devflow.hermes.session")


class HermesSessionManager:
    def __init__(self, db: Session):
        self._db = db

    def create_session(self, user_id: str, profile_name: str = "default", model_id: str = "hermes-agent", display_name: str = None) -> HermesSession:
        session = HermesSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_name=profile_name,
            model_id=model_id,
            display_name=display_name or f"对话 {datetime.now(timezone.utc).strftime('%m/%d %H:%M')}",
        )
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def get_session(self, session_id: str) -> Optional[HermesSession]:
        return self._db.query(HermesSession).filter(HermesSession.id == session_id).first()

    def list_sessions(self, user_id: str, limit: int = 50) -> List[HermesSession]:
        return (
            self._db.query(HermesSession)
            .filter(HermesSession.user_id == user_id)
            .order_by(desc(HermesSession.updated_at))
            .limit(limit)
            .all()
        )

    def delete_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        self._db.query(HermesMessage).filter(HermesMessage.session_id == session_id).delete()
        self._db.delete(session)
        self._db.commit()
        return True

    def rename_session(self, session_id: str, display_name: str) -> Optional[HermesSession]:
        session = self.get_session(session_id)
        if not session:
            return None
        session.display_name = display_name
        self._db.commit()
        self._db.refresh(session)
        return session

    def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> List[HermesMessage]:
        return (
            self._db.query(HermesMessage)
            .filter(HermesMessage.session_id == session_id)
            .order_by(HermesMessage.timestamp)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        thinking_content: str = None,
        tool_calls: list = None,
        model: str = None,
        is_streaming: bool = False,
        is_interrupted: bool = False,
    ) -> HermesMessage:
        msg = HermesMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            thinking_content=thinking_content,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            model=model,
            is_streaming=is_streaming,
            is_interrupted=is_interrupted,
        )
        self._db.add(msg)
        session = self.get_session(session_id)
        if session:
            session.message_count = (session.message_count or 0) + 1
            session.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(msg)
        return msg

    def build_openai_messages(self, history: List[HermesMessage], new_message: str) -> List[Dict[str, str]]:
        messages = []
        for msg in history:
            if msg.role in ("user", "assistant", "system"):
                messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": new_message})
        return messages

    def truncate_context_if_needed(self, messages: List[Dict[str, str]], max_tokens: int = 128000) -> List[Dict[str, str]]:
        est_tokens = sum(len(m.get("content", "")) // 3 for m in messages)
        if est_tokens <= max_tokens:
            return messages
        max_rounds = 10
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        kept = non_system[-(max_rounds * 2):]
        return system_msgs + kept
