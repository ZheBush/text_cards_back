from pydantic import BaseModel
from typing import Optional


class CardCreate(BaseModel):
    question: str
    answer: str


class CardUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None


class CardResponse(BaseModel):
    id: str
    question: str
    answer: str
    user_id: str
    card_list_id: str
