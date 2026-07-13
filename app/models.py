from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Boolean, Date, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from typing import Optional

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)

    boards_owned = relationship('Board', foreign_keys='Board.owner_id', back_populates='owner')
    board_members = relationship('BoardMember', back_populates='user')
    cards_created = relationship('Card', foreign_keys='Card.created_by', back_populates='author')
    cards_assigned = relationship('Card', foreign_keys='Card.assignee_id', back_populates='assignee')
    comments = relationship('Comment', back_populates='user')

    __table_args__ = (Index('idx_users_version', 'version'),)

    def __repr__(self):
        return f'<User {self.username}>'


class Board(Base):
    __tablename__ = 'boards'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)

    owner = relationship('User', foreign_keys=[owner_id], back_populates='boards_owned')
    members = relationship('BoardMember', back_populates='board', cascade='all, delete-orphan')
    columns = relationship('Column', back_populates='board', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_boards_version', 'version'),
    )

    def __repr__(self):
        return f'<Board {self.title}>'


class BoardMember(Base):
    __tablename__ = 'board_members'

    board_id: Mapped[int] = mapped_column(Integer, ForeignKey('boards.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default='member')
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)

    board = relationship('Board', back_populates='members')
    user = relationship('User', back_populates='board_members')

    __table_args__ = (
        Index('idx_board_members_user_id', 'user_id'),
        Index('idx_board_members_version', 'version'),
    )

    def __repr__(self):
        return f'<BoardMember board={self.board_id} user={self.user_id} role={self.role}>'


class Column(Base):
    __tablename__ = 'columns'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board_id: Mapped[int] = mapped_column(Integer, ForeignKey('boards.id', ondelete='CASCADE'), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)

    board = relationship('Board', back_populates='columns')
    cards = relationship('Card', back_populates='column', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_columns_version', 'version'),
    )

    def __repr__(self):
        return f'<Column {self.title}>'


class Card(Base):
    __tablename__ = 'cards'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    column_id: Mapped[int] = mapped_column(Integer, ForeignKey('columns.id', ondelete='CASCADE'), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    deadline: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archived_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    version: Mapped[int] = mapped_column(Integer, default=1)


    column = relationship('Column', back_populates='cards')
    assignee = relationship('User', foreign_keys=[assignee_id], back_populates='cards_assigned')
    author = relationship('User', foreign_keys=[created_by], back_populates='cards_created')
    comments = relationship('Comment', back_populates='card', cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')"),
        Index('idx_cards_column_id', 'column_id'),
        Index('idx_cards_assignee_id', 'assignee_id'),
        Index('idx_cards_deadline', 'deadline'),
        Index('idx_cards_priority', 'priority'),
        Index('idx_cards_archived', 'is_archived'),
        Index('idx_cards_version', 'version'),
    )

    def __repr__(self):
        return f'<Card {self.title}>'


class Comment(Base):
    __tablename__ = 'comments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    version: Mapped[int] = mapped_column(Integer, default=1)

    card = relationship('Card', back_populates='comments')
    user = relationship('User', back_populates='comments')

    __table_args__ = (
        Index('idx_comments_card_id', 'card_id'),
        Index('idx_comments_version', 'version'),
    )

    def __repr__(self):
        return f'<Comment {self.id} on card {self.card_id}>'


class AuditLog(Base):
    __tablename__ = 'audit_log'

    id: Mapped[int] = mapped_column(Integer, primary_key = True, index = True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    old_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_audit_log_user_id', 'user_id'),
        Index('idx_audit_log_action', 'action'),
        Index('idx_audit_log_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_log_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} {self.entity_type} {self.entity_id} by {self.user_id}>"