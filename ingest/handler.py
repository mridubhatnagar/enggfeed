"""IngestHandler — orchestrates the full RSS ingest pipeline.

Pipeline per source:
    fetch feed → collect new articles → for each article:
        _fetch_thumbnail → insert blog row
        → get_content → call_llm (tags + prerequisites)
        → _process_tag per tag
        → _process_prerequisite per prerequisite
        → _process_summary (PARTIAL + FULL tier)
        → _process_simplify (FULL tier only)

Tag / prerequisite normalisation:
    lowercase + strip + collapse hyphens/underscores/spaces → embed
    → find_similar (threshold from constants) → merge or insert
    Each normalisation decision is wrapped in an OTel span.

Error handling:
    - RSS feed unavailable → log, skip source
    - LLM failure on a single article → log, skip that article
    - og:image scraping fails silently → thumbnail = None
"""

import logging
import re
from decimal import Decimal

import requests
import sentry_sdk
from bs4 import BeautifulSoup
from opentelemetry import trace

from blog.service import BlogService, BlogSourceService
from constants import (
    ANTHROPIC_MODEL,
    CONTENT_TIER_LIMITED_MAX_WORDS,
    CONTENT_TIER_PARTIAL_MAX_WORDS,
    EMBEDDING_COST_PER_MILLION_TOKENS,
    EMBEDDING_MODEL,
    LLM_INPUT_COST_PER_MILLION_TOKENS,
    LLM_OUTPUT_COST_PER_MILLION_TOKENS,
    TAG_SIMILARITY_THRESHOLD,
)
from exceptions import LLMUnreachableError, RSSFeedError
from ingest.embedder import Embedder
from ingest.models import LLMUsageCallType
from ingest.service import LLMUsageService
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from prompts.ingest import INGEST_PROMPT
from prompts.simplify import SIMPLIFY_PROMPT
from prompts.summary import SUMMARY_PROMPT
from rss_client import RSSClient
from simplify.service import SimplifyService
from summary.service import SummaryService
from tags.service import BlogTagService, TagService
from utils import call_llm

logger = logging.getLogger(__name__)

# Module-level OTel tracer — used for normalisation spans.
tracer = trace.get_tracer("enggsystemfeed.ingest")


class IngestHandler:
    """Orchestrates the RSS ingest pipeline.

    Constructor dependencies are injected — no internal instantiation.
    """

    def __init__(
        self,
        blog_source_service: BlogSourceService,
        blog_service: BlogService,
        tag_service: TagService,
        blog_tag_service: BlogTagService,
        prerequisite_service: PrerequisiteService,
        blog_prerequisite_service: BlogPrerequisiteService,
        summary_service: SummaryService,
        simplify_service: SimplifyService,
        rss_client: RSSClient,
        embedder: Embedder,
        llm_usage_service: LLMUsageService,
    ) -> None:
        self.blog_source_service = blog_source_service
        self.blog_service = blog_service
        self.tag_service = tag_service
        self.blog_tag_service = blog_tag_service
        self.prerequisite_service = prerequisite_service
        self.blog_prerequisite_service = blog_prerequisite_service
        self.summary_service = summary_service
        self.simplify_service = simplify_service
        self.rss_client = rss_client
        self.embedder = embedder
        self.llm_usage_service = llm_usage_service

    def trigger_job(self) -> None:
        """Run the daily ingest job across all RSS sources.

        Fetches all sources from DB, processes each one independently.
        Errors for a single source do not abort remaining sources.
        """
        sources = self.blog_source_service.list_all_sources()
        logger.info("Ingest job started — %d source(s) to process", len(sources))

        for source in sources:
            try:
                self._process_source(source)
            except Exception as exc:
                sentry_sdk.capture_exception(exc)
                logger.error(
                    "Unhandled error processing source '%s': %s",
                    getattr(source, "source", source),
                    exc,
                    exc_info=True,
                )

        logger.info("Ingest job complete")

    def _process_source(self, source) -> None:
        """Fetch feed, find new articles, insert oldest-first."""
        feed_url: str = source.rss_feed_link
        source_id = source.id
        source_name: str = source.source

        try:
            items = self.rss_client.get_feed(feed_url)
        except RSSFeedError as exc:
            sentry_sdk.capture_exception(exc)
            logger.error("RSS feed error for source '%s': %s", source_name, exc)
            return

        if not items:
            logger.info("No items in feed for source '%s'", source_name)
            return

        last_blog = self.blog_service.get_last_blog_by_source_id(source_id)
        last_known_guid: str | None = last_blog.guid if last_blog else None

        new_items: list[dict] = []
        for item in items:
            if last_known_guid and item["guid"] == last_known_guid:
                break
            new_items.append(item)

        if not new_items:
            logger.info("No new articles for source '%s'", source_name)
            return

        new_items.reverse()
        logger.info(
            "Inserting %d new article(s) for source '%s'",
            len(new_items),
            source_name,
        )

        for item in new_items:
            try:
                self._process_article(item, source_id, feed_url)
            except Exception as exc:
                logger.error(
                    "Error processing article guid='%s' from source '%s': %s",
                    item.get("guid"),
                    source_name,
                    exc,
                    exc_info=True,
                )

    def _process_article(self, item: dict, source_id, feed_url: str) -> None:
        """Insert one article and run the tagging + prerequisite pipeline."""
        from blog.models import Blog

        guid: str = item["guid"]
        title: str = item["title"]
        link: str = item["link"]
        published_at = item["published_at"]
        word_count: int = item["word_count"]

        if self.blog_service.get_blog_by_guid(guid):
            logger.debug("Blog already exists, skipping guid='%s'", guid)
            return

        thumbnail = self._fetch_thumbnail(link)

        blog = Blog(
            guid=guid,
            link=link,
            title=title,
            thumbnail=thumbnail,
            word_count=word_count,
            published_at=published_at,
            blog_source_id=source_id,
        )
        self.blog_service.insert_blog(blog)
        blog_id = blog.id
        logger.debug("Inserted blog guid='%s' id='%s'", guid, blog_id)

        if word_count < CONTENT_TIER_LIMITED_MAX_WORDS:
            logger.debug(
                "Skipping chunk/embed and LLM for limited-tier article guid='%s' "
                "(word_count=%d)",
                guid,
                word_count,
            )
            return

        try:
            content = self.rss_client.get_content(feed_url, guid)
        except RSSFeedError as exc:
            sentry_sdk.capture_exception(exc)
            logger.error("Could not fetch content for guid='%s': %s", guid, exc)
            return

        prompt = INGEST_PROMPT.format(title=title, content=content)
        try:
            llm_result, usage = call_llm(prompt, return_usage=True)
        except LLMUnreachableError as exc:
            sentry_sdk.capture_exception(exc)
            logger.error(
                "LLM call failed for guid='%s', skipping tagging/prerequisites: %s",
                guid,
                exc,
            )
            return
        self._record_chat_usage(
            blog_id, LLMUsageCallType.TAG_PREREQUISITE_EXTRACTION, usage
        )

        tags: list[str] = llm_result.get("tags", [])
        prerequisites: list[str] = llm_result.get("prerequisites", [])
        logger.info(
            "LLM result for guid='%s': raw=%s tags=%s prerequisites=%s",
            guid,
            llm_result,
            tags,
            prerequisites,
        )

        linked_tag_ids: set = set()
        for tag_name in tags:
            try:
                self._process_tag(blog_id, tag_name, linked_tag_ids)
            except Exception as exc:
                sentry_sdk.capture_exception(exc)
                logger.error(
                    "Error processing tag '%s' for guid='%s': %s",
                    tag_name,
                    guid,
                    exc,
                )

        linked_prerequisite_ids: set = set()
        for topic_name in prerequisites:
            try:
                self._process_prerequisite(blog_id, topic_name, linked_prerequisite_ids)
            except Exception as exc:
                sentry_sdk.capture_exception(exc)
                logger.error(
                    "Error processing prerequisite '%s' for guid='%s': %s",
                    topic_name,
                    guid,
                    exc,
                )

        try:
            self._process_summary(blog_id, title, content)
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            logger.error("Error generating summary for guid='%s': %s", guid, exc)

        if word_count >= CONTENT_TIER_PARTIAL_MAX_WORDS:
            try:
                self._process_simplify(blog_id, title, content)
            except Exception as exc:
                sentry_sdk.capture_exception(exc)
                logger.error("Error generating simplify for guid='%s': %s", guid, exc)

    def _process_summary(self, blog_id: str, title: str, content: str) -> None:
        """Generate and persist the summary for one article at ingest time."""
        prompt = SUMMARY_PROMPT.format(title=title, content=content)
        llm_result, usage = call_llm(prompt, return_usage=True)
        summary_content = {
            "short_summary": llm_result.get("short_summary", ""),
            "key_points": llm_result.get("key_points", []),
        }
        self.summary_service.create_summary(blog_id, summary_content)
        self._record_chat_usage(blog_id, LLMUsageCallType.SUMMARY, usage)

    def _process_simplify(self, blog_id: str, title: str, content: str) -> None:
        """Generate and persist the ELI5 simplify for one article at ingest time."""
        prompt = SIMPLIFY_PROMPT.format(title=title, content=content)
        llm_result, usage = call_llm(prompt, return_usage=True)
        simplify_content = llm_result.get("simplify", "")
        self.simplify_service.create_simplify(blog_id, simplify_content)
        self._record_chat_usage(blog_id, LLMUsageCallType.SIMPLIFY, usage)

    def _fetch_thumbnail(self, link: str) -> str | None:
        """Scrape og:image from the article URL. Returns None on any failure."""
        try:
            resp = requests.get(link, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("meta", property="og:image")
            if tag and tag.get("content"):
                return tag["content"]
        except Exception as exc:
            logger.debug("og:image scrape failed for '%s': %s", link, exc)
        return None

    def _normalize_name(self, name: str) -> str:
        """Lowercase, strip, collapse hyphens/underscores/spaces to '-'."""
        name = name.lower().strip()
        name = re.sub(r"[\s_]+", "-", name)
        name = re.sub(r"-{2,}", "-", name)
        return name

    def _process_tag(self, blog_id: str, tag_name: str, linked_tag_ids: set) -> None:
        """Normalize, embed, find-or-create tag, link to blog.

        Wraps the normalisation decision in an OTel span with attributes:
            tag.candidate, tag.normalized, tag.similarity_score,
            tag.action, tag.canonical (on merge).
        """
        normalized = self._normalize_name(tag_name)
        embedding, usage = self.embedder.embed(normalized, return_usage=True)
        self._record_embedding_usage(blog_id, LLMUsageCallType.TAG_EMBEDDING, usage)
        match, score = self.tag_service.find_similar_tag(
            embedding, TAG_SIMILARITY_THRESHOLD
        )

        with tracer.start_as_current_span("tag.normalize") as span:
            span.set_attribute("tag.candidate", tag_name)
            span.set_attribute("tag.normalized", normalized)
            if score is not None:
                span.set_attribute("tag.similarity_score", score)

            if match is not None:
                span.set_attribute("tag.action", "merge")
                span.set_attribute("tag.canonical", match.tag)
                tag_id = match.tag_id
            else:
                span.set_attribute("tag.action", "insert")
                new_tag = self.tag_service.create_tag(normalized, embedding)
                tag_id = new_tag.tag_id

        if tag_id in linked_tag_ids:
            logger.debug("Tag '%s' already linked to blog, skipping", normalized)
            return
        self.blog_tag_service.create_blog_tag(blog_id, tag_id)
        linked_tag_ids.add(tag_id)

    def _process_prerequisite(
        self, blog_id: str, topic_name: str, linked_prerequisite_ids: set
    ) -> None:
        """Normalize, embed, find-or-create prerequisite, link to blog.

        Wraps the normalisation decision in an OTel span with attributes:
            prerequisite.candidate, prerequisite.normalized,
            prerequisite.similarity_score, prerequisite.action,
            prerequisite.canonical (on merge).
        """
        normalized = self._normalize_name(topic_name)
        embedding, usage = self.embedder.embed(normalized, return_usage=True)
        self._record_embedding_usage(
            blog_id, LLMUsageCallType.PREREQUISITE_EMBEDDING, usage
        )
        match, score = self.prerequisite_service.find_similar_prerequisite(
            embedding, TAG_SIMILARITY_THRESHOLD
        )

        with tracer.start_as_current_span("prerequisite.normalize") as span:
            span.set_attribute("prerequisite.candidate", topic_name)
            span.set_attribute("prerequisite.normalized", normalized)
            if score is not None:
                span.set_attribute("prerequisite.similarity_score", score)

            if match is not None:
                span.set_attribute("prerequisite.action", "merge")
                span.set_attribute("prerequisite.canonical", match.topic_name)
                prerequisite_id = match.id
            else:
                span.set_attribute("prerequisite.action", "insert")
                new_prereq = self.prerequisite_service.create_prerequisite(
                    normalized, embedding
                )
                prerequisite_id = new_prereq.id

        if prerequisite_id in linked_prerequisite_ids:
            logger.debug(
                "Prerequisite '%s' already linked to blog, skipping", normalized
            )
            return
        self.blog_prerequisite_service.create_blog_prerequisite(
            blog_id, prerequisite_id
        )
        linked_prerequisite_ids.add(prerequisite_id)

    def _record_chat_usage(
        self, blog_id: str, call_type: LLMUsageCallType, usage: dict
    ) -> None:
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]
        cost = Decimal(input_tokens) / Decimal(1_000_000) * Decimal(
            str(LLM_INPUT_COST_PER_MILLION_TOKENS)
        ) + Decimal(output_tokens) / Decimal(1_000_000) * Decimal(
            str(LLM_OUTPUT_COST_PER_MILLION_TOKENS)
        )
        self.llm_usage_service.create_llm_usage(
            blog_id=blog_id,
            call_type=call_type.value,
            provider="bedrock",
            model=ANTHROPIC_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
        )

    def _record_embedding_usage(
        self, blog_id: str, call_type: LLMUsageCallType, usage: dict
    ) -> None:
        total_tokens = usage["total_tokens"]
        cost = (
            Decimal(total_tokens)
            / Decimal(1_000_000)
            * Decimal(str(EMBEDDING_COST_PER_MILLION_TOKENS))
        )
        self.llm_usage_service.create_llm_usage(
            blog_id=blog_id,
            call_type=call_type.value,
            provider="openai",
            model=EMBEDDING_MODEL,
            input_tokens=None,
            output_tokens=None,
            total_tokens=total_tokens,
            cost_usd=cost,
        )
