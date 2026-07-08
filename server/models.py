from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, CheckConstraint, UniqueConstraint,
    Boolean, Date
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    version = Column(Integer, default=1)

    boards_owned = relationship('Board', foreign_keys='Board.owner_id', back_populates='owner')
    board_members = relationship('BoardMember', back_populates='user')
    cards_created = relationship('Card', foreign_keys='Card.created_by', back_populates='author')
    cards_assigned = relationship('Card', foreign_keys='Card.assignee_id', back_populates='assignee')
    comments = relationship('Comment', back_populates='user')

    def __repr__(self):
        return f'<User {self.username}>'


class Board(Base):
    __tablename__ = 'boards'

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    version = Column(Integer, default=1)

    owner = relationship('User', foreign_keys=[owner_id], back_populates='boards_owned')
    members = relationship('BoardMember', back_populates='board', cascade='all, delete-orphan')
    columns = relationship('Column', back_populates='board', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Board {self.title}>'


class BoardMember(Base):
    __tablename__ = 'board_members'

    board_id = Column(Integer, ForeignKey('boards.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role = Column(String(20), default='member')
    joined_at = Column(DateTime, server_default=func.now())
    version = Column(Integer, default=1)

    board = relationship('Board', back_populates='members')
    user = relationship('User', back_populates='board_members')

    def __repr__(self):
        return f'<BoardMember board={self.board_id} user={self.user_id} role={self.role}>'


class Column(Base):
    __tablename__ = 'columns'

    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('boards.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(100), nullable=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    version = Column(Integer, default=1)

    board = relationship('Board', back_populates='columns')
    cards = relationship('Card', back_populates='column', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Column {self.title}>'


class Card(Base):
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True)
    column_id = Column(Integer, ForeignKey('columns.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    position = Column(Integer, default=0)
    assignee_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    deadline = Column(Date)
    priority = Column(String(20), default='medium')
    created_by = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime)
    archived_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    version = Column(Integer, default=1)


    column = relationship('Column', back_populates='cards')
    assignee = relationship('User', foreign_keys=[assignee_id], back_populates='cards_assigned')
    author = relationship('User', foreign_keys=[created_by], back_populates='cards_created')
    comments = relationship('Comment', back_populates='card', cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint("priority IN ('low', 'medium', 'high')"),
    )

    def __repr__(self):
        return f'<Card {self.title}>'


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey('cards.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    version = Column(Integer, default=1)

    card = relationship('Card', back_populates='comments')
    user = relationship('User', back_populates='comments')

    def __repr__(self):
        return f'<Comment {self.id} on card {self.card_id}>'