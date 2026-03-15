from pydantic import BaseModel
from datetime import datetime


class GroupCreate(BaseModel):
    name: str


class GroupResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    created_by: str
    members_count: int = 0


class AddUserToGroup(BaseModel):
    user_id: str
    role_in_group: str = 'member'