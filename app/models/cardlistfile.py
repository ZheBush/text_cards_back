from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.core.utils import generate_uuid


class CardListFile(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    file_key = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    card_list_id = Column(String, ForeignKey("card_lists.id", ondelete="CASCADE"), nullable=True)
    card_id = Column(String, ForeignKey("cards.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    card_list = relationship("CardList", back_populates="files")
    card = relationship("Card", back_populates="files")
    user = relationship("User", back_populates="files")