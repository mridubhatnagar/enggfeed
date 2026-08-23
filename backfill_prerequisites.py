"""
One-off script to generate content for prerequisites that were created at
ingest time but never clicked by a user (so never generated lazily).
No RSS dependency — topic-name-keyed LLM call only — so this should
succeed for all rows unless the LLM call itself fails transiently.

Run:
    docker exec -it app_enggsystemfeed python backfill_prerequisites.py
"""

from database import SessionLocal
from exceptions import LLMUnreachableError
from prerequisites.dao import PrerequisiteDAO
from prerequisites.models import Prerequisite
from prerequisites.service import PrerequisiteService
from prompts.prerequisites import PREREQUISITES_PROMPT
from utils import call_llm


def main() -> None:
    db = SessionLocal()
    service = PrerequisiteService(PrerequisiteDAO(db))
    try:
        missing = db.query(Prerequisite).filter(Prerequisite.content.is_(None)).all()
        print(f"Found {len(missing)} prerequisite(s) with no content.", flush=True)

        created = failed = 0
        for i, prereq in enumerate(missing, 1):
            try:
                prompt = PREREQUISITES_PROMPT.format(topic_name=prereq.topic_name)
                llm_result = call_llm(prompt)
                new_content = {
                    "definition": llm_result.get("definition", ""),
                    "why_it_matters": llm_result.get("why_it_matters", ""),
                    "example": llm_result.get("example", ""),
                    "deep_dive": llm_result.get("deep_dive", ""),
                }
                # Goes through the service/DAO layer (not a raw model mutation)
                # so the @cache.set decorator on update() correctly overwrites
                # any stale None-content entry a prior user click may have cached.
                service.update_prerequisite(prereq.topic_name, new_content)
                print(
                    f"  [{i}/{len(missing)}] created: '{prereq.topic_name}'", flush=True
                )
                created += 1
            except LLMUnreachableError as exc:
                print(
                    f"  [{i}/{len(missing)}] failed: '{prereq.topic_name}': {exc}",
                    flush=True,
                )
                failed += 1

        print()
        print(f"created={created} failed={failed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
