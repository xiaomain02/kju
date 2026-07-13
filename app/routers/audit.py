from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User, AuditLog, Board
from auth import get_current_user
from dependencies import is_board_owner

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("/")
async def get_audit_logs(
        limit: int = 10,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    boards = db.query(Board).filter(Board.owner_id == current_user.id).all()
    if not boards:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owners can view audit logs"
        )

    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs