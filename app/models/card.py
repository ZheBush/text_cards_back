from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.utils import generate_uuid


class Card(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True, default=generate_uuid)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    card_list_id = Column(String, ForeignKey("card_lists.id"), nullable=False)

    card_list = relationship("CardList", back_populates="cards")
    files = relationship("CardListFile", back_populates="card", cascade="all, delete-orphan")
