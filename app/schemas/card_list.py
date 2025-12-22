from datetime import datetime
from pydantic import BaseModel


class CardListResponse(BaseModel):
    id: str
    filename: str
    cards_count: int


class FileUploadResponse(BaseModel):
    card_list_id: str
    filename: str
    message: str
