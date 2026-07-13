from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User, Board, Column
from schemas import ColumnCreate, ColumnUpdate, ColumnResponse
from auth import get_current_user
from dependencies import can_read_board, can_manage_columns
from utils.logger import log_action

router = APIRouter(prefix="/api/columns", tags=["columns"])


@router.get("/boards/{board_id}/columns", response_model=List[ColumnResponse])
async def get_columns(
        board_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if not can_read_board(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this board"
        )

    columns = db.query(Column).filter(Column.board_id == board_id).order_by(Column.position).all()
    return columns


@router.post("/boards/{board_id}/columns", response_model=ColumnResponse)
async def create_column(
        board_id: int,
        column_data: ColumnCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if not can_manage_columns(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can create columns"
        )

    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")

    new_column = Column(
        board_id=board_id,
        title=column_data.title,
        position=column_data.position or 0
    )
    db.add(new_column)
    db.commit()
    db.refresh(new_column)

    log_action(
        db=db,
        user_id=current_user.id,
        board_id=board_id,  # 👈 ДОБАВЛЕНО
        action="create",
        entity_type="column",
        entity_id=new_column.id,
        new_values={
            "title": new_column.title,
            "board_id": new_column.board_id,
            "board_name": board.title,
            "position": new_column.position
        }
    )

    return new_column


@router.put("/{column_id}", response_model=ColumnResponse)
async def update_column(
        column_id: int,
        column_data: ColumnUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    column = db.query(Column).filter(Column.id == column_id).first()
    if not column:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")

    board = db.query(Board).filter(Board.id == column.board_id).first()
    if board.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can update columns"
        )

    if column.version != column_data.version:
        db.refresh(column)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Column was updated by another user",
                "current_version": column.version
            }
        )

    old_values = {
        "title": column.title,
        "position": column.position
    }

    for key, value in column_data.model_dump(exclude_unset=True).items():
        if key != "version":
            setattr(column, key, value)

    column.version += 1
    db.commit()
    db.refresh(column)

    log_action(
        db=db,
        user_id=current_user.id,
        board_id=column.board_id,  # 👈 ДОБАВЛЕНО
        action="update",
        entity_type="column",
        entity_id=column_id,
        old_values=old_values,
        new_values={
            "title": column.title,
            "position": column.position,
            "board_name": board.title
        }
    )

    return column


@router.delete("/{column_id}")
async def delete_column(
        column_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    column = db.query(Column).filter(Column.id == column_id).first()
    if not column:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")

    board = db.query(Board).filter(Board.id == column.board_id).first()
    if board.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can delete columns"
        )

    log_action(
        db=db,
        user_id=current_user.id,
        board_id=column.board_id,  # 👈 ДОБАВЛЕНО
        action="delete",
        entity_type="column",
        entity_id=column_id,
        old_values={
            "title": column.title,
            "board_id": column.board_id,
            "board_name": board.title
        }
    )

    db.delete(column)
    db.commit()
    return {"message": "Column deleted successfully"}