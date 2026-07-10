from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Board, Card, Column
from app.schemas import CardCreate, CardUpdate, CardResponse, CardMove
from app.auth import get_current_user
from app.dependencies import (
    can_read_board, can_create_cards, can_edit_own_cards,
    is_board_member, is_overdue
)

router = APIRouter(prefix="/api/cards", tags=["cards"])

@router.get("/columns/{column_id}/cards", response_model=List[CardResponse])
async def get_cards(
    column_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    column = db.query(Column).filter(Column.id == column_id).first()
    if not column:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")
    
    if not can_read_board(column.board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this board"
        )
    
    cards = db.query(Card).filter(Card.column_id == column_id).order_by(Card.position).all()
    
    result = []
    for card in cards:
        response = CardResponse.model_validate(card)
        response.is_overdue = is_overdue(card.deadline)
        
        if card.assignee_id:
            assignee = db.query(User).filter(User.id == card.assignee_id).first()
            response.assignee = assignee
        if card.created_by:
            creator = db.query(User).filter(User.id == card.created_by).first()
            response.creator = creator
        
        result.append(response)
    
    return result

@router.post("/columns/{column_id}/cards", response_model=CardResponse)
async def create_card(
    column_id: int,
    card_data: CardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    column = db.query(Column).filter(Column.id == column_id).first()
    if not column:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")
    
    if not can_create_cards(column.board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create cards in this board"
        )
    
    if card_data.assignee_id:
        if not is_board_member(column.board_id, card_data.assignee_id, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee must be a member of this board"
            )
    
    max_position = db.query(Card).filter(Card.column_id == column_id).count()
    
    new_card = Card(
        column_id=column_id,
        title=card_data.title,
        description=card_data.description,
        position=max_position,
        assignee_id=card_data.assignee_id,
        deadline=card_data.deadline,
        priority=card_data.priority.value,
        created_by=current_user.id
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    
    response = CardResponse.model_validate(new_card)
    response.is_overdue = is_overdue(new_card.deadline)
    
    if new_card.assignee_id:
        assignee = db.query(User).filter(User.id == new_card.assignee_id).first()
        response.assignee = assignee
    creator = db.query(User).filter(User.id == new_card.created_by).first()
    response.creator = creator
    
    return response

@router.get("/{card_id}", response_model=CardResponse)
async def get_card(
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
    
    response = CardResponse.model_validate(card)
    response.is_overdue = is_overdue(card.deadline)
    
    if card.assignee_id:
        assignee = db.query(User).filter(User.id == card.assignee_id).first()
        response.assignee = assignee
    creator = db.query(User).filter(User.id == card.created_by).first()
    response.creator = creator
    
    return response

@router.put("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: int,
    card_data: CardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_edit_own_cards(card_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this card"
        )
    
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    if card.version != card_data.version:
        db.refresh(card)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Card was updated by another user",
                "current_version": card.version
            }
        )
    
    if card_data.assignee_id is not None:
        board = db.query(Board).filter(Board.id == card.column.board_id).first()
        if not is_board_member(board.id, card_data.assignee_id, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee must be a member of this board"
            )
    
    for key, value in card_data.model_dump(exclude_unset=True).items():
        if key != "version":
            setattr(card, key, value)
    
    card.version += 1
    db.commit()
    db.refresh(card)
    
    response = CardResponse.model_validate(card)
    response.is_overdue = is_overdue(card.deadline)
    
    if card.assignee_id:
        assignee = db.query(User).filter(User.id == card.assignee_id).first()
        response.assignee = assignee
    creator = db.query(User).filter(User.id == card.created_by).first()
    response.creator = creator
    
    return response

@router.delete("/{card_id}")
async def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_edit_own_cards(card_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this card"
        )
    
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    db.delete(card)
    db.commit()
    return {"message": "Card deleted successfully"}

@router.patch("/{card_id}/move", response_model=CardResponse)
async def move_card(
    card_id: int,
    move_data: CardMove,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_edit_own_cards(card_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to move this card"
        )
    
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    
    target_column = db.query(Column).filter(Column.id == move_data.target_column_id).first()
    if not target_column:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target column not found")
    
    if target_column.board_id != card.column.board_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot move card to a different board"
        )
    
    board = db.query(Board).filter(Board.id == target_column.board_id).first()
    if not can_read_board(board.id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this board"
        )
    
    old_column_id = card.column_id
    target_position = max(0, move_data.position)

    if old_column_id == move_data.target_column_id:
        ordered_cards = db.query(Card).filter(
            Card.column_id == old_column_id,
            Card.id != card_id
        ).order_by(Card.position, Card.id).all()

        target_position = min(target_position, len(ordered_cards))
        ordered_cards.insert(target_position, card)

        for position, item in enumerate(ordered_cards):
            item.position = position
    else:
        old_cards = db.query(Card).filter(
            Card.column_id == old_column_id,
            Card.id != card_id
        ).order_by(Card.position, Card.id).all()

        for position, item in enumerate(old_cards):
            item.position = position

        target_cards = db.query(Card).filter(
            Card.column_id == move_data.target_column_id,
            Card.id != card_id
        ).order_by(Card.position, Card.id).all()

        target_position = min(target_position, len(target_cards))
        card.column_id = move_data.target_column_id
        target_cards.insert(target_position, card)

        for position, item in enumerate(target_cards):
            item.position = position
    
    db.commit()
    db.refresh(card)
    
    response = CardResponse.model_validate(card)
    response.is_overdue = is_overdue(card.deadline)
    
    if card.assignee_id:
        assignee = db.query(User).filter(User.id == card.assignee_id).first()
        response.assignee = assignee
    creator = db.query(User).filter(User.id == card.created_by).first()
    response.creator = creator
    
    return response

@router.patch("/{card_id}/assign")
async def assign_executor(
    card_id: int,
    assignee_id: int,
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
    
    if not is_board_member(board.id, assignee_id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must be a member of this board"
        )
    
    card.assignee_id = assignee_id
    db.commit()
    db.refresh(card)
    
    return {"message": "Assignee updated successfully"}
