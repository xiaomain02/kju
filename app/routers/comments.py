from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User, Card, Comment, Board
from schemas import CommentCreate, CommentUpdate, CommentResponse
from auth import get_current_user
from dependencies import can_read_board, can_delete_comment
from utils.logger import log_action

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.get("/cards/{card_id}/comments", response_model=List[CommentResponse])
async def get_comments(
        card_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    board = db.query(Board).filter(Board.id == card.column.board_id).first()
    if not can_read_board(board.id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this board"
        )

    comments = db.query(Comment).filter(Comment.card_id == card_id).order_by(Comment.created_at).all()

    result = []
    for comment in comments:
        response = CommentResponse.model_validate(comment)
        user = db.query(User).filter(User.id == comment.user_id).first()
        response.user = user
        result.append(response)

    return result


@router.post("/cards/{card_id}/comments", response_model=CommentResponse)
async def add_comment(
        card_id: int,
        comment_data: CommentCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    board = db.query(Board).filter(Board.id == card.column.board_id).first()
    board_id = board.id if board else None

    if not can_read_board(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this board"
        )

    new_comment = Comment(
        card_id=card_id,
        user_id=current_user.id,
        content=comment_data.content
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    log_action(
        db=db,
        user_id=current_user.id,
        board_id=board_id,  # 👈 ДОБАВЛЕНО
        action="create",
        entity_type="comment",
        entity_id=new_comment.id,
        new_values={
            "card_id": card_id,
            "card_name": card.title,
            "content": new_comment.content
        }
    )

    response = CommentResponse.model_validate(new_comment)
    response.user = current_user

    return response


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
        comment_id: int,
        comment_data: CommentUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only author can edit this comment"
        )

    if comment.version != comment_data.version:
        db.refresh(comment)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Comment was updated by another user",
                "current_version": comment.version
            }
        )

    old_values = {
        "content": comment.content,
        "card_id": comment.card_id
    }

    # Получаем название карточки и board_id для лога
    card = db.query(Card).filter(Card.id == comment.card_id).first()
    card_title = card.title if card else None
    board_id = card.column.board_id if card else None

    comment.content = comment_data.content
    comment.version += 1
    db.commit()
    db.refresh(comment)

    log_action(
        db=db,
        user_id=current_user.id,
        board_id=board_id,  # 👈 ДОБАВЛЕНО
        action="update",
        entity_type="comment",
        entity_id=comment_id,
        old_values=old_values,
        new_values={
            "content": comment.content,
            "card_id": comment.card_id,
            "card_name": card_title
        }
    )

    response = CommentResponse.model_validate(comment)
    response.user = current_user

    return response


@router.delete("/{comment_id}")
async def delete_comment(
        comment_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if not can_delete_comment(comment_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this comment"
        )

    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    # Получаем название карточки и board_id для лога
    card = db.query(Card).filter(Card.id == comment.card_id).first()
    card_title = card.title if card else None
    board_id = card.column.board_id if card else None

    log_action(
        db=db,
        user_id=current_user.id,
        board_id=board_id,  # 👈 ДОБАВЛЕНО
        action="delete",
        entity_type="comment",
        entity_id=comment_id,
        old_values={
            "card_id": comment.card_id,
            "card_name": card_title,
            "content": comment.content
        }
    )

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted successfully"}