from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime, date
from typing import Optional

# ---------- AUTH ----------
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ---------- BOARDS ----------
class BoardCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class BoardUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class BoardResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class BoardDetailResponse(BoardResponse):
    members: list['BoardMemberResponse'] = []

# ---------- BOARD MEMBERS ----------
class MemberAdd(BaseModel):
    email: EmailStr

class BoardMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    joined_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ---------- COLUMNS ----------
class ColumnCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    position: Optional[int] = 0

class ColumnUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    position: Optional[int] = None

class ColumnResponse(BaseModel):
    id: int
    board_id: int
    title: str
    position: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

class ColumnDetailResponse(ColumnResponse):
    cards: list['CardResponse'] = []

# ---------- CARDS ----------
class CardCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    deadline: Optional[date] = None
    priority: Priority = Priority.MEDIUM

class CardUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    deadline: Optional[date] = None
    priority: Optional[Priority] = None

class CardMove(BaseModel):
    target_column_id: int
    position: int = Field(..., ge=0)

class CardResponse(BaseModel):
    id: int
    column_id: int
    title: str
    description: Optional[str]
    position: int
    assignee_id: Optional[int]
    assignee: Optional[UserResponse] = None
    deadline: Optional[date]
    priority: Priority = Priority.MEDIUM
    created_by: int
    creator: Optional[UserResponse] = None
    created_at: datetime
    updated_at: Optional[datetime]
    is_overdue: bool = False
    
    model_config = ConfigDict(from_attributes=True)

# ---------- COMMENTS ----------
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)

class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)

class CommentResponse(BaseModel):
    id: int
    card_id: int
    user_id: int
    user: Optional[UserResponse] = None
    content: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

# ---------- FORWARD DECLARATIONS ----------
BoardDetailResponse.model_rebuild()
ColumnDetailResponse.model_rebuild()
CardResponse.model_rebuild()
CommentResponse.model_rebuild()