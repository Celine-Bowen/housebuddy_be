from datetime import datetime

from pydantic import BaseModel


class BuddyStatusUpdate(BaseModel):
    is_active: bool = False
    note: str | None = None


class BuddyStatusResponse(BaseModel):
    is_active: bool
    note: str | None


class BuddyPoolItem(BaseModel):
    user_id: int
    name: str
    note: str
    connected: bool


class BuddyConnectionResponse(BaseModel):
    connected: bool


class BuddyConnectionItem(BaseModel):
    peer_user_id: int
    peer_name: str
    note: str
    source: str
    created_at: datetime
