from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import User, Board, BoardMember, Card, Column, Comment
from app.schemas import BoardRole
from datetime import date


def is_board_owner(board_id: int, user_id: int, db: Session) -> bool:
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        return False
    return board.owner_id == user_id


def is_board_member(board_id: int, user_id: int, db: Session) -> bool:
    member = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_id
    ).first()
    return member is not None


def get_user_role(board_id: int, user_id: int, db: Session) -> Optional[str]:
    board = db.query(Board).filter(Board.id == board_id).first()
    if board and board.owner_id == user_id:
        return BoardRole.OWNER
    
    member = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_id
    ).first()
    
    if member:
        return member.role
    
    return None


def can_read_board(board_id: int, user_id: int, db: Session) -> bool:
    if is_board_owner(board_id, user_id, db):
        return True
    return is_board_member(board_id, user_id, db)


def can_create_cards(board_id: int, user_id: int, db: Session) -> bool:
    role = get_user_role(board_id, user_id, db)
    if role is None:
        return False
    return role in [BoardRole.MEMBER, BoardRole.OWNER]


def can_edit_own_cards(card_id: int, user_id: int, db: Session) -> bool:
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        return False
    
    board = db.query(Board).filter(Board.id == card.column.board_id).first()
    if not board:
        return False
    
    if board.owner_id == user_id:
        return True
    
    role = get_user_role(board.id, user_id, db)
    if role == BoardRole.MEMBER:
        return card.created_by == user_id
    
    return False


def can_delete_comment(comment_id: int, user_id: int, db: Session) -> bool:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        return False
    
    card = db.query(Card).filter(Card.id == comment.card_id).first()
    if not card:
        return False
    
    board = db.query(Board).filter(Board.id == card.column.board_id).first()
    if not board:
        return False
    
    if board.owner_id == user_id:
        return True
    
    role = get_user_role(board.id, user_id, db)
    if role == BoardRole.MEMBER:
        return comment.user_id == user_id
    
    return False


def can_manage_columns(board_id: int, user_id: int, db: Session) -> bool:
    return is_board_owner(board_id, user_id, db)


def can_manage_members(board_id: int, user_id: int, db: Session) -> bool:
    return is_board_owner(board_id, user_id, db)


def can_delete_board(board_id: int, user_id: int, db: Session) -> bool:
    return is_board_owner(board_id, user_id, db)


def is_overdue(deadline) -> bool:
    if not deadline:
        return False
    return date.today() > deadline


# Legacy compatibility
def can_edit_card(card_id: int, user_id: int, db: Session) -> bool:
    return can_edit_own_cards(card_id, user_id, db)


def can_delete_card(card_id: int, user_id: int, db: Session) -> bool:
    return can_edit_own_cards(card_id, user_id, db)


def can_move_card(card_id: int, user_id: int, db: Session) -> bool:
    return can_edit_own_cards(card_id, user_id, db)