from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


# ============================================
# ENUMS
# ============================================

class Priority(str, Enum):
    """Приоритет карточки"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BoardRole(str, Enum):
    """Роль участника доски"""
    OWNER = "owner"
    MEMBER = "member"


# ============================================
# AUTH (Аутентификация)
# ============================================

class UserCreate(BaseModel):
    """Регистрация нового пользователя"""
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")


class UserLogin(BaseModel):
    """Вход в систему"""
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Пароль")


class Token(BaseModel):
    """JWT токен"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ============================================
# USERS (Пользователи)
# ============================================

class UserResponse(BaseModel):
    """Ответ с данными пользователя"""
    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Обновление профиля пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Новое имя пользователя")
    email: Optional[EmailStr] = Field(None, description="Новый email")
    password: Optional[str] = Field(None, min_length=6, description="Новый пароль")
    version: int = Field(..., description="Текущая версия пользователя (для предотвращения коллизий)")


# ============================================
# BOARD MEMBERS (Участники доски)
# ============================================

class MemberAdd(BaseModel):
    """Добавление участника в доску"""
    email: EmailStr = Field(..., description="Email пользователя, которого нужно добавить")


class BoardMemberResponse(BaseModel):
    """Ответ с данными участника доски"""
    user_id: int
    username: str
    email: str
    role: BoardRole
    joined_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# BOARDS (Доски)
# ============================================

class BoardCreate(BaseModel):
    """Создание новой доски"""
    title: str = Field(..., min_length=1, max_length=100, description="Название доски")
    #description: Optional[str] = Field(None, description="Описание доски")


class BoardUpdate(BaseModel):
    """Обновление доски"""
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="Новое название доски")
    #description: Optional[str] = Field(None, description="Новое описание доски")
    version: int = Field(..., description="Текущая версия доски (для предотвращения коллизий)")


class BoardResponse(BaseModel):
    """Ответ с данными доски (базовый)"""
    id: int
    title: str
    #description: Optional[str] = None
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True)


class BoardDetailResponse(BoardResponse):
    """Ответ с данными доски (с участниками)"""
    members: List[BoardMemberResponse] = []


# ============================================
# COLUMNS (Колонки)
# ============================================

class ColumnCreate(BaseModel):
    """Создание новой колонки"""
    title: str = Field(..., min_length=1, max_length=100, description="Название колонки")
    position: Optional[int] = Field(0, description="Позиция колонки (порядок)")


class ColumnUpdate(BaseModel):
    """Обновление колонки"""
    title: Optional[str] = Field(None, min_length=1, max_length=100, description="Новое название колонки")
    position: Optional[int] = Field(None, description="Новая позиция колонки")
    version: int = Field(..., description="Текущая версия колонки (для предотвращения коллизий)")


class ColumnResponse(BaseModel):
    """Ответ с данными колонки"""
    id: int
    board_id: int
    title: str
    position: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True)


class ColumnDetailResponse(ColumnResponse):
    """Ответ с данными колонки (с карточками)"""
    cards: List["CardResponse"] = []


# ============================================
# CARDS (Карточки)
# ============================================

class CardCreate(BaseModel):
    """Создание новой карточки"""
    title: str = Field(..., min_length=1, max_length=200, description="Заголовок карточки")
    description: Optional[str] = Field(None, description="Описание карточки")
    assignee_id: Optional[int] = Field(None, description="ID исполнителя (пользователя)")
    deadline: Optional[date] = Field(None, description="Дедлайн (только дата)")
    priority: Priority = Field(Priority.MEDIUM, description="Приоритет: low, medium, high")


class CardUpdate(BaseModel):
    """Обновление карточки"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Новый заголовок")
    description: Optional[str] = Field(None, description="Новое описание")
    assignee_id: Optional[int] = Field(None, description="Новый исполнитель")
    deadline: Optional[date] = Field(None, description="Новый дедлайн")
    priority: Optional[Priority] = Field(None, description="Новый приоритет")
    version: int = Field(..., description="Текущая версия карточки (для предотвращения коллизий)")


class CardMove(BaseModel):
    """Перемещение карточки между колонками"""
    target_column_id: int = Field(..., description="ID колонки, куда перемещаем")
    position: int = Field(..., ge=0, description="Новая позиция в колонке")


class CardResponse(BaseModel):
    """Ответ с данными карточки"""
    id: int
    column_id: int
    title: str
    description: Optional[str] = None
    position: int
    assignee_id: Optional[int] = None
    assignee: Optional[UserResponse] = None
    deadline: Optional[date] = None
    priority: Priority = Priority.MEDIUM
    created_by: int
    creator: Optional[UserResponse] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_overdue: bool = False
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# COMMENTS (Комментарии)
# ============================================

class CommentCreate(BaseModel):
    """Создание комментария"""
    content: str = Field(..., min_length=1, description="Текст комментария")


class CommentUpdate(BaseModel):
    """Обновление комментария"""
    content: str = Field(..., min_length=1, description="Новый текст комментария")
    version: int = Field(..., description="Текущая версия комментария (для предотвращения коллизий)")


class CommentResponse(BaseModel):
    """Ответ с данными комментария"""
    id: int
    card_id: int
    user_id: int
    user: Optional[UserResponse] = None
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# FORWARD DECLARATIONS (для циклических ссылок)
# ============================================

# Обновляем модели, которые ссылаются друг на друга
BoardDetailResponse.model_rebuild()
ColumnDetailResponse.model_rebuild()
CardResponse.model_rebuild()
CommentResponse.model_rebuild()
Token.model_rebuild()