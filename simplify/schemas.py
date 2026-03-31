from datetime import datetime

from pydantic import BaseModel

from blog.schemas import BlogItem


class SimplifyContent(BaseModel):
    content: str
    updated_at: datetime


class SimplifyDetail(BaseModel):
    blog: BlogItem
    simplify: SimplifyContent
