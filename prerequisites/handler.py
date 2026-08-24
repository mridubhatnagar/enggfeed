from exceptions import NotFoundError
from prerequisites.schemas import Primer, PrerequisiteDetail
from prerequisites.service import PrerequisiteService


class PrerequisiteHandler:
    def __init__(self, prerequisite_service: PrerequisiteService) -> None:
        self.prerequisite_service = prerequisite_service

    def get_prerequisite(self, topic_name: str) -> PrerequisiteDetail:
        prereq = self.prerequisite_service.get_prerequisite_by_topic_name(topic_name)
        if prereq is None or prereq.content is None:
            raise NotFoundError(f"Prerequisite not found: {topic_name}")

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
