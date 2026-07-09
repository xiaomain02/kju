from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)
    
    owned_boards = relationship("Board", back_populates="owner")
    board_memberships = relationship("BoardMember", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    created_cards = relationship("Card", foreign_keys="Card.created_by", back_populates="creator")
    assigned_cards = relationship("Card", foreign_keys="Card.assignee_id", back_populates="assignee")


class Board(Base):
    __tablename__ = "boards"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)
    
    owner = relationship("User", back_populates="owned_boards")
    members = relationship("BoardMember", back_populates="board", cascade="all, delete-orphan")
    columns = relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan")


class BoardMember(Base):
    __tablename__ = "board_members"
    
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(20), default="reader")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    board = relationship("Board", back_populates="members")
    user = relationship("User", back_populates="board_memberships")


class BoardColumn(Base):
    __tablename__ = "columns"
    
    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), nullable=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)
    
    board = relationship("Board", back_populates="columns")
    cards = relationship("Card", back_populates="column", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True, index=True)
    column_id = Column(Integer, ForeignKey("columns.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    position = Column(Integer, default=0)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deadline = Column(Date, nullable=True)
    priority = Column(String(20), default="medium")
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)
    
    column = relationship("BoardColumn", back_populates="cards")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_cards")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_cards")
    comments = relationship("Comment", back_populates="card", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    version = Column(Integer, default=1)
    
    card = relationship("Card", back_populates="comments")
    user = relationship("User", back_populates="comments")