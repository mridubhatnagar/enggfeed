from auth.utils import decode_jwt_token
from exceptions import NotFoundError, UnauthorizedError
from prerequisites.schemas import Primer, PrerequisiteDetail
from prerequisites.service import PrerequisiteService
from prompts.prerequisites import PREREQUISITES_PROMPT
from utils import call_llm, check_refresh_due


class PrerequisiteHandler:
    def __init__(self, prerequisite_service: PrerequisiteService) -> None:
        self.prerequisite_service = prerequisite_service

    def get_prerequisite(self, topic_name: str, token: str | None) -> PrerequisiteDetail:
        if not token:
            raise UnauthorizedError("Authentication required")
        decode_jwt_token(token)

        prereq = self.prerequisite_service.get_prerequisite_by_topic_name(topic_name)
        if prereq is None:
            raise NotFoundError(f"Prerequisite not found: {topic_name}")

        if prereq.content is None or check_refresh_due(prereq.updated_at):
            prompt = PREREQUISITES_PROMPT.format(topic_name=topic_name)
            llm_result = call_llm(prompt)
            new_content = {
                "definition": llm_result.get("definition", ""),
                "why_it_matters": llm_result.get("why_it_matters", ""),
                "example": llm_result.get("example", ""),
                "deep_dive": llm_result.get("deep_dive", ""),
            }
            prereq = self.prerequisite_service.update_prerequisite(topic_name, new_content)

        content = prereq.content
        primer = Primer(
            definition=content.get("definition", ""),
            why_it_matters=content.get("why_it_matters", ""),
            example=content.get("example", ""),
        )

        return PrerequisiteDetail(
            topic_name=prereq.topic_name,
            primer=primer,
            deep_dive=content.get("deep_dive", ""),
            updated_at=prereq.updated_at,
        )
