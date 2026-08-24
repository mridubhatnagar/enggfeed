import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class LLMUsageCallType(str, enum.Enum):
    TAG_PREREQUISITE_EXTRACTION = "tag_prerequisite_extraction"
    SUMMARY = "summary"
    SIMPLIFY = "simplify"
    TAG_EMBEDDING = "tag_embedding"
    PREREQUISITE_EMBEDDING = "prerequisite_embedding"
    PREREQUISITE_CONTENT = "prerequisite_content"


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blog_id = Column(UUID(as_uuid=True), ForeignKey("blog.id"), nullable=False)
    call_type = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(12, 8), nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(tz=timezone.utc), nullable=False
    )
