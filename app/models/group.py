from sqlalchemy import Column, String, DateTime, ForeignKey, Table, Enum, select, func
from sqlalchemy.orm import relationship, column_property
from datetime import datetime, timezone
from app.core.database import Base
from app.core.utils import generate_uuid


user_group = Table(
    'user_group',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id'), primary_key=True),
    Column('group_id', String, ForeignKey('groups.id'), primary_key=True),
    Column('role_in_group', String, default='member')
)


class Group(Base):
    __tablename__ = 'groups'

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    created_by = Column(String, ForeignKey('users.id'), nullable=False)

    creator = relationship('User', foreign_keys=[created_by])
    members = relationship('User', secondary=user_group, back_populates='groups')
    card_lists = relationship('CardList', back_populates='group', cascade='all, delete-orphan')

    members_count = column_property(
        select(func.count(user_group.c.user_id))
        .where(user_group.c.group_id == id)
        .correlate_except(user_group)
        .scalar_subquery()
    )