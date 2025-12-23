from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, func, select
from sqlalchemy.orm import column_property, relationship

from app.core.database import Base
from app.core.utils import generate_uuid
from app.models.card import Card


class CardList(Base):
    __tablename__ = "card_lists"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="card_lists")
    cards = relationship("Card", back_populates="card_list", cascade="all, delete-orphan")

    cards_count = column_property(
        select(func.count(Card.id))
        .where(Card.card_list_id == id)
        .correlate_except(Card)
        .scalar_subquery()
    )
