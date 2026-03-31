from datetime import datetime

from pydantic import BaseModel

from blog.schemas import BlogItem


class SummaryContent(BaseModel):
    short_summary: str
    key_points: list[str]
    updated_at: datetime


class SummaryDetail(BaseModel):
    blog: BlogItem
    summary: SummaryContent
