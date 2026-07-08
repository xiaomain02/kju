from app.schemas import UserUpdate

@router.put("/users/me", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверка версии
    if current_user.version != user_data.version:
        db.refresh(current_user)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "User profile was updated by another session",
                "current_version": current_user.version
            }
        )
    
    # Обновляем поля
    if user_data.username:
        # Проверяем, что username свободен
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
    return current_user