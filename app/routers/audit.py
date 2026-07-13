from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import User, AuditLog, Board, BoardMember, Column, Card, Comment
from auth import get_current_user
from dependencies import is_board_owner

router = APIRouter(prefix="/api/audit", tags=["Audit"])


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

    columns = db.query(Column).filter(Column.board_id == board_id).all()
    column_ids = [col.id for col in columns]

    cards = db.query(Card).filter(Card.column_id.in_(column_ids)).all()
    card_ids = [card.id for card in cards]

    comments = db.query(Comment).filter(Comment.card_id.in_(card_ids)).all()
    comment_ids = [comment.id for comment in comments]

    entity_ids_for_board = column_ids + card_ids + comment_ids + [board_id]

    logs_query = db.query(AuditLog).filter(
        AuditLog.entity_type.in_(["board", "column", "card", "comment"]),
        AuditLog.entity_id.in_(entity_ids_for_board)
    ).order_by(AuditLog.created_at.desc())

    total = logs_query.count()

    logs = logs_query.offset(offset).limit(limit).all()

    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "user": user.full_name if user else f"User {log.user_id}",
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": log.old_values,
            "new_values": log.new_values,
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


@router.get("/my-logs")
async def get_my_audit_logs(
        limit: int = 50,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    user_boards = db.query(Board).filter(Board.owner_id == current_user.id).all()
    board_ids = [b.id for b in user_boards]

    if not board_ids:
        return {
            "message": "You don't own any boards",
            "logs": []
        }

    columns = db.query(Column).filter(Column.board_id.in_(board_ids)).all()
    column_ids = [col.id for col in columns]

    cards = db.query(Card).filter(Card.column_id.in_(column_ids)).all()
    card_ids = [card.id for card in cards]

    comments = db.query(Comment).filter(Comment.card_id.in_(card_ids)).all()
    comment_ids = [comment.id for comment in comments]

    all_entity_ids = board_ids + column_ids + card_ids + comment_ids

    logs_query = db.query(AuditLog).filter(
        AuditLog.entity_id.in_(all_entity_ids)
    ).order_by(AuditLog.created_at.desc()).limit(limit)

    logs = logs_query.all()

    result = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "user": user.full_name if user else f"User {log.user_id}",
            "user_id": log.user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_values": log.old_values,
            "new_values": log.new_values,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })

    return {
        "total": len(result),
        "logs": result
    }