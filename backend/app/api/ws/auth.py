from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User


async def verify_token(token: str, db: Session) -> Optional[User]:
    from app.utils.security import decode_token
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user
