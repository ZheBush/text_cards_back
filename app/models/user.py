import enum

from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.core.utils import generate_uuid


class UserRole(str, enum.Enum):
    user = "user"
    manager = "manager"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)

    files = relationship("CardListFile", back_populates="user", cascade="all, delete-orphan")
    groups = relationship('Group', secondary='user_group', back_populates='members', lazy='selectin')
    card_lists = relationship("CardList", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy='selectin')

