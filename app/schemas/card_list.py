from typing import Optional, List
from pydantic import BaseModel


class CardListResponse(BaseModel):
    id: str
    title: str
    cards_count: int


class FileUploadResponse(BaseModel):
    card_list_id: str
    title: str
    message: str


class GroupFileUploadResponse(BaseModel):
    group_id: Optional[str] = None
    card_list_id: Optional[str] = None
    title: str
    message: str
    cards_count: int
    member_count: Optional[int] = None
    cards_count: int
    member_count: int


class PaginatedCardListResponse(BaseModel):
    items: List[CardListResponse]
    total: int
    page: int
    per_page: int
    pages: int