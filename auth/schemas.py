import uuid

from pydantic import BaseModel


class UserDetail(BaseModel):
    user_id: uuid.UUID
    name: str
    profile_url: str
