from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Board, BoardMember
from app.schemas import (
    BoardCreate, BoardUpdate, BoardResponse, BoardDetailResponse,
    BoardMemberResponse, MemberAdd, MemberRoleUpdate, BoardRole
)
from app.auth import get_current_user
from app.dependencies import (
    is_board_owner, is_board_member, can_read_board,
    can_manage_members, can_delete_board
)

router = APIRouter(prefix="/api/boards", tags=["boards"])

@router.get("/", response_model=List[BoardResponse])
async def get_boards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    owned = db.query(Board).filter(Board.owner_id == current_user.id).all()
    
    member_board_ids = db.query(BoardMember.board_id).filter(
        BoardMember.user_id == current_user.id
    ).subquery()
    member_boards = db.query(Board).filter(Board.id.in_(member_board_ids)).all()
    
    boards = {board.id: board for board in owned}
    for board in member_boards:
        boards[board.id] = board
    
    return list(boards.values())

@router.post("/", response_model=BoardResponse)
async def create_board(
    board_data: BoardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_board = Board(
        title=board_data.title,
        owner_id=current_user.id
    )
    db.add(new_board)
    db.flush()
    
    board_member = BoardMember(
        board_id=new_board.id,
        user_id=current_user.id,
        role=BoardRole.OWNER
    )
    db.add(board_member)
    db.commit()
    db.refresh(new_board)
    
    return new_board

@router.get("/{board_id}", response_model=BoardDetailResponse)
async def get_board(
    board_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_read_board(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this board"
        )
    
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    
    members = db.query(BoardMember).filter(BoardMember.board_id == board_id).all()
    member_responses = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        member_responses.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": member.role,
            "joined_at": member.joined_at
        })
    
    result = BoardDetailResponse.model_validate(board)
    result.members = member_responses
    return result

@router.put("/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: int,
    board_data: BoardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not is_board_owner(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can update this board"
        )
    
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    
    if board.version != board_data.version:
        db.refresh(board)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Board was updated by another user",
                "current_version": board.version
            }
        )
    
    if board_data.title is not None:
        board.title = board_data.title
    
    board.version += 1
    db.commit()
    db.refresh(board)
    return board

@router.delete("/{board_id}")
async def delete_board(
    board_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_delete_board(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can delete this board"
        )
    
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    
    db.delete(board)
    db.commit()
    return {"message": "Board deleted successfully"}

@router.post("/{board_id}/members", response_model=BoardMemberResponse)
async def add_member(
    board_id: int,
    member_data: MemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_manage_members(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can add members"
        )
    
    user_to_add = db.query(User).filter(User.email == member_data.email).first()
    if not user_to_add:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    existing = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_to_add.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already a member")
    
    new_member = BoardMember(
        board_id=board_id,
        user_id=user_to_add.id,
        role=BoardRole.READER
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return {
        "user_id": user_to_add.id,
        "username": user_to_add.username,
        "email": user_to_add.email,
        "role": BoardRole.READER,
        "joined_at": new_member.joined_at
    }

@router.patch("/{board_id}/members/{user_id}/role")
async def change_member_role(
    board_id: int,
    user_id: int,
    role_data: MemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_manage_members(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can change member roles"
        )
    
    if is_board_owner(board_id, user_id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change role of board owner"
        )
    
    member = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    
    member.role = role_data.role
    db.commit()
    db.refresh(member)
    
    return {"message": f"Role changed to {role_data.role}"}

@router.delete("/{board_id}/members/{user_id}")
async def remove_member(
    board_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not can_manage_members(board_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only board owner can remove members"
        )
    
    if is_board_owner(board_id, user_id, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove board owner"
        )
    
    member = db.query(BoardMember).filter(
        BoardMember.board_id == board_id,
        BoardMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    
    db.delete(member)
    db.commit()
    
    return {"message": "Member removed successfully"}