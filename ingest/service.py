import uuid
from datetime import datetime
from decimal import Decimal

from ingest.dao import ILLMUsageDAO


class LLMUsageService:
    def __init__(self, dao: ILLMUsageDAO) -> None:
        self.dao = dao

    def create_llm_usage(
        self,
        blog_id: uuid.UUID,
        call_type: str,
        provider: str,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int,
        cost_usd: Decimal,
    ):
        return self.dao.create(
            blog_id,
            call_type,
            provider,
            model,
            input_tokens,
            output_tokens,
            total_tokens,
            cost_usd,
        )

    def get_daily_costs(self, since: datetime):
        return self.dao.list_daily_costs(since)

    def get_monthly_costs(self, since: datetime):
        return self.dao.list_monthly_costs(since)

    def get_total_costs(self):
        return self.dao.get_total_costs()
