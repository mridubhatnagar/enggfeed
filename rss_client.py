from datetime import datetime, timezone

import feedparser
from bs4 import BeautifulSoup

from exceptions import RSSFeedError


class RSSClient:
    """Fetches and parses RSS feeds. No article URL scraping — content comes from the feed only."""

    def get_feed(self, feed_url: str) -> list[dict]:
        """Fetch and parse the RSS feed, returning all items latest-first.

        Each item contains: guid, title, link, published_at, word_count, content.
        Raises RSSFeedError if the feed cannot be fetched or parsed.
        """
        try:
            feed = feedparser.parse(feed_url)
        except Exception as exc:
            raise RSSFeedError(f"Failed to fetch RSS feed: {feed_url}") from exc

        if feed.bozo and feed.bozo_exception and not feed.entries:
            raise RSSFeedError(
                f"Malformed RSS feed {feed_url}: {feed.bozo_exception}"
            )

        items: list[dict] = []
        for entry in feed.entries:
            content = self._extract_content(entry)
            plain_text = self._strip_html(content)
            word_count = len(plain_text.split()) if plain_text.strip() else 0

            published_at = self._parse_published(entry)

            items.append(
                {
                    "guid": entry.get("id") or entry.get("link", ""),
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published_at": published_at,
                    "word_count": word_count,
                    "content": content,
                }
            )

        return items

    def get_content(self, feed_url: str, guid: str) -> str:
        """Fetch the RSS feed and return the article text for the item matching guid.

        Returns content from <content:encoded> or <description>.
        No scraping of the article URL.
        Raises RSSFeedError if the feed cannot be fetched or the guid is not found.
        """
        try:
            feed = feedparser.parse(feed_url)
        except Exception as exc:
            raise RSSFeedError(f"Failed to fetch RSS feed: {feed_url}") from exc

        for entry in feed.entries:
            entry_guid = entry.get("id") or entry.get("link", "")
            if entry_guid == guid:
                return self._extract_content(entry)

        raise RSSFeedError(f"Article with guid '{guid}' not found in feed: {feed_url}")

    def _extract_content(self, entry: dict) -> str:
        """Extract raw content from a feedparser entry."""
        if hasattr(entry, "content") and entry.content:
            return entry.content[0].get("value", "")
        return entry.get("summary", "")

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags and return plain text."""
        if not html:
            return ""
        return BeautifulSoup(html, "html.parser").get_text(separator=" ")

    def _parse_published(self, entry: dict) -> datetime | None:
        """Parse the published date from a feedparser entry."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            import calendar
            ts = calendar.timegm(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        return None
