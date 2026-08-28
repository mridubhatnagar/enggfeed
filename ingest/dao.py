import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
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

    @abstractmethod
    def list_daily_costs(self, since: datetime): ...

    @abstractmethod
    def list_monthly_costs(self, since: datetime): ...

    @abstractmethod
    def get_total_costs(self): ...

    @abstractmethod
    def list_costs_by_call_type(self, since: datetime): ...


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

    def list_daily_costs(self, since: datetime):
        try:
            day = func.date_trunc("day", LLMUsage.created_at).label("day")
            return (
                self.db.query(
                    day,
                    func.count(LLMUsage.id).label("calls"),
                    func.sum(LLMUsage.cost_usd).label("cost_usd"),
                )
                .filter(LLMUsage.created_at >= since)
                .group_by(day)
                .order_by(day)
                .all()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to list daily LLM costs: {exc}") from exc

    def list_monthly_costs(self, since: datetime):
        try:
            month = func.date_trunc("month", LLMUsage.created_at).label("month")
            return (
                self.db.query(
                    month,
                    func.count(LLMUsage.id).label("calls"),
                    func.sum(LLMUsage.cost_usd).label("cost_usd"),
                )
                .filter(LLMUsage.created_at >= since)
                .group_by(month)
                .order_by(month)
                .all()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to list monthly LLM costs: {exc}") from exc

    def get_total_costs(self):
        try:
            return self.db.query(
                func.count(LLMUsage.id).label("calls"),
                func.sum(LLMUsage.cost_usd).label("cost_usd"),
            ).one()
        except Exception as exc:
            raise DatabaseError(f"Failed to get total LLM costs: {exc}") from exc

    def list_costs_by_call_type(self, since: datetime):
        try:
            return (
                self.db.query(
                    LLMUsage.call_type,
                    func.count(LLMUsage.id).label("calls"),
                    func.sum(LLMUsage.cost_usd).label("cost_usd"),
                )
                .filter(LLMUsage.created_at >= since)
                .group_by(LLMUsage.call_type)
                .order_by(LLMUsage.call_type)
                .all()
            )
        except Exception as exc:
            raise DatabaseError(
                f"Failed to list LLM costs by call type: {exc}"
            ) from exc
