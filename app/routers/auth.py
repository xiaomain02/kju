from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserCreate, UserLogin, Token, UserResponse, UserUpdate
from auth import verify_password, get_password_hash, create_access_token, get_current_user
from utils.logger import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_action(
        db=db,
        user_id=new_user.id,
        action="register",
        entity_type="user",
        entity_id=new_user.id,
        new_values={"username": new_user.username, "email": new_user.email}
    )
    
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    log_action(
        db=db,
        user_id=user.id,
        action="login",
        entity_type="user",
        entity_id=user.id,
        new_values={"email": user.email}
    )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.put("/users/me", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    old_values = {
        "username": current_user.username,
        "email": current_user.email,
    }

    if current_user.version != user_data.version:
        db.refresh(current_user)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "User profile was updated by another session",
                "current_version": current_user.version
            }
        )
    
    if user_data.username:
        existing = db.query(User).filter(
            User.username == user_data.username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_data.username
    
    if user_data.email:
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
        current_user.email = user_data.email
    
    if user_data.password:
        current_user.password_hash = get_password_hash(user_data.password)
    
    current_user.version += 1
    db.commit()
    db.refresh(current_user)

    log_action(
        db=db,
        user_id=current_user.id,
        action="update",
        entity_type="user",
        entity_id=current_user.id,
        old_values=old_values,
        new_values={"username": current_user.username, "email": current_user.email}
    )
    return current_user