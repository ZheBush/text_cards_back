from datetime import datetime
from pydantic import BaseModel


class CardListResponse(BaseModel):
    id: str
    title: str
    cards_count: int


class FileUploadResponse(BaseModel):
    card_list_id: str
    title: str
    message: str
