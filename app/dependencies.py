from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Board, BoardMember, Card, Column, Comment

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

def check_board_access(board_id: int, user_id: int, db: Session) -> bool:
    """Проверяет, имеет ли пользователь доступ к доске (владелец или участник)"""
    if is_board_owner(board_id, user_id, db):
        return True
    return is_board_member(board_id, user_id, db)

def can_edit_card(card_id: int, user_id: int, db: Session) -> bool:
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        return False
    
    board = db.query(Board).filter(Board.id == card.column.board_id).first()
    if not board:
        return False
    
    # Owner может всё
    if board.owner_id == user_id:
        return True
    
    # Member может редактировать только свои карточки
    return card.created_by == user_id

def can_delete_card(card_id: int, user_id: int, db: Session) -> bool:
    return can_edit_card(card_id, user_id, db)

def can_move_card(card_id: int, user_id: int, db: Session) -> bool:
    return can_edit_card(card_id, user_id, db)

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
    
    # Owner может удалить любой комментарий
    if board.owner_id == user_id:
        return True
    
    # Member может удалить только свой
    return comment.user_id == user_id

def is_overdue(deadline) -> bool:
    """Проверяет, просрочен ли дедлайн"""
    if not deadline:
        return False
    from datetime import date
    return date.today() > deadline