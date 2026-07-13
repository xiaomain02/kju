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
        limit: int = 50,
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

    # Получаем ID всех колонок этой доски
    column_ids = [col.id for col in db.query(Column).filter(Column.board_id == board_id).all()]
    # Получаем ID всех карточек этих колонок
    card_ids = [card.id for card in db.query(Card).filter(Card.column_id.in_(column_ids)).all()]
    # Получаем ID всех комментариев этих карточек
    comment_ids = [comment.id for comment in db.query(Comment).filter(Comment.card_id.in_(card_ids)).all()]

    # 👇 ВАЖНО: собираем все ID, которые относятся к этой доске
    allowed_entity_ids = [board_id] + column_ids + card_ids + comment_ids

    # 👇 Запрашиваем логи ТОЛЬКО по этим ID и нужным типам
    logs_query = db.query(AuditLog).filter(
        AuditLog.entity_id.in_(allowed_entity_ids),
        AuditLog.entity_type.in_(['board', 'column', 'card', 'comment', 'board_member'])
    ).order_by(AuditLog.created_at.desc())

    total = logs_query.count()
    logs = logs_query.offset(offset).limit(limit).all()

    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()

        old_values = parse_json_field(log.old_values)
        new_values = parse_json_field(log.new_values)

        result.append({
            "id": log.id,
            "user": user.username if user else f"User {log.user_id}",
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": old_values,
            "new_values": new_values,
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