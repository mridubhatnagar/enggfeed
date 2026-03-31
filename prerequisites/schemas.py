from datetime import datetime

from pydantic import BaseModel


class Primer(BaseModel):
    definition: str
    why_it_matters: str
    example: str


class PrerequisiteDetail(BaseModel):
    topic_name: str
    primer: Primer
    deep_dive: str
    updated_at: datetime
