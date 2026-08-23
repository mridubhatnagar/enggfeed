import uuid
from abc import ABC, abstractmethod
from decimal import Decimal

from sqlalchemy.orm import Session

from exceptions import DatabaseError
from ingest.models import LLMUsage


class ILLMUsageDAO(ABC):
    @abstractmethod
    def create(
        self,
        blog_id: uuid.UUID,
        call_type: str,
        provider: str,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int,
        cost_usd: Decimal,
    ): ...


class LLMUsageDAO(ILLMUsageDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        blog_id: uuid.UUID,
        call_type: str,
        provider: str,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int,
        cost_usd: Decimal,
    ) -> LLMUsage:
        try:
            usage = LLMUsage(
                blog_id=blog_id,
                call_type=call_type,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
            )
            self.db.add(usage)
            self.db.commit()
            self.db.refresh(usage)
            return usage
        except Exception as exc:
            raise DatabaseError(f"Failed to create LLM usage record: {exc}") from exc
