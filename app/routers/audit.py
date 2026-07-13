from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from database import get_db
from models import User, AuditLog, Board, BoardMember, Column, Card, Comment
from auth import get_current_user
from dependencies import is_board_owner

router = APIRouter(prefix="/api/audit", tags=["Audit"])


def parse_json_field(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except:
        return None


@router.get("/board/{board_id}")
async def get_board_audit_logs(
    board_id: int,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    if not is_board_owner(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can view audit logs"
        )

    # 👇 ПРОСТОЙ ЗАПРОС ПО board_id
    logs_query = db.query(AuditLog).filter(
        AuditLog.board_id == board_id
    ).order_by(AuditLog.created_at.desc())

    total = logs_query.count()
    logs = logs_query.offset(offset).limit(limit).all()

    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "user": user.username if user else f"User {log.user_id}",
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": parse_json_field(log.old_values),
            "new_values": parse_json_field(log.new_values),
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "board_id": board_id,
        "board_title": board.title,
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": result
    }