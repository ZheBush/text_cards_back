from sqlalchemy import Column, ForeignKey, String, func, select, DateTime
from sqlalchemy.orm import column_property, relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.core.utils import generate_uuid
from app.models.card import Card


class CardList(Base):
    __tablename__ = "card_lists"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    group_id = Column(String, ForeignKey("groups.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="card_lists")
    cards = relationship("Card", back_populates="card_list", cascade="all, delete-orphan")
    group = relationship("Group", back_populates="card_lists")
    files = relationship("CardListFile", back_populates="card_list", cascade="all, delete-orphan")

    cards_count = column_property(
        select(func.count(Card.id))
        .where(Card.card_list_id == id)
        .correlate_except(Card)
        .scalar_subquery()
    )