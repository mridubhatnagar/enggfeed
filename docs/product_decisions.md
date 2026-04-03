# Product Decisions: Engineering Blog Aggregator

## Why
- **Fragmented discovery**: The only way to find engineering blogs today is to visit each company's page individually.
- **Complex content**: The technology discussed is often difficult to understand without prior context.
This product solves for both — one place to discover, read, and understand engineering blogs.

## What
A one stop aggregator platform for reading engineering blogs from big tech companies.
All users can browse and filter blogs by company, and read the full article on the original site.
Signed-in users can additionally browse by topic tags, see prerequisite topics, and get AI summaries and simplified explanations.


## Product Features

## Auth
- Google Auth only
- Sign in button in top navbar

## User Tiers
- **Guest**: Browse, filter by company
- **Signed-in**: All features unlocked — topic tags, prerequisites, summary, simplify

## Content Tiers (based on RSS content word count)
| Tier | Condition | Features |
|------|-----------|----------|
| Limited | < 150 words | Full Read only + badge |
| Partial | 150–300 words | Full Read + Summary + Tags, no ELI5 |
| Full | 300+ words | All features |

## Card Visuals
- `og:image` scraped from the article page at ingest — URL stored, image served from their CDN (unique thumbnail per article)
- No image generation

## Tags
- LLM freeform — tags are not constrained to a predefined list
- Clickable on cards to filter the feed
- **Open:** Whether to feed existing RSS categories to LLM as hints — decide after evaluating tagging quality in practice
- **Normalization pipeline:** string normalize (lowercase, strip, collapse separators) → embed → cosine similarity check against existing tags (threshold: 0.88) → use existing canonical tag or insert new. Same pipeline as prerequisites.
- False merge risk accepted — threshold is tunable at evaluation stage. When uncertain, prefer fragmentation over false merge.

## ELI5 (Simplify)
- On-demand (not pre-computed)
- Free for signed-in users
- No rate limiting — cached per article, shared across all users. First request pays the LLM cost, all subsequent requests are served from cache.

## Prerequisites

- Signed-in users only
- Content tier gating: same as tags (Partial + Full only, excluded for Limited)
- Two-step feature:
  1. **Extraction** — at ingest, LLM extracts prerequisite topic names from the article (e.g., "Raft consensus", "LSM trees"). Displayed on the article card.
  2. **Explanation** — on-demand when a user clicks a prerequisite topic name. Opens a modal. No page navigation.
- **Modal — two levels (single LLM call, both generated together):**
  - **Primer** (default view) — structured: 1-2 line definition, "Why it matters", "Example". Enough context to recognise the concept before reading.
  - **Deep dive** (read more) — detailed technical explanation, revealed on clicking "Read more" within the modal
- **Caching:** keyed by `topic_name` — one cached entry per topic, shared across all articles and users. Lookup order: cache → DB → LLM
- **Refresh:** configurable interval (default: 7 days) — first cache miss after expiry regenerates for everyone. Periodic regeneration is intentional — newer LLM calls may produce better results.
- **Rate limiting:** none — cached by topic name, shared across all users and articles. First request pays the LLM cost, all subsequent requests are served from cache.

---

## Ads

- **Ad network:** EthicalAds (developer-targeted, text-based, no tracking)
- **Placement:**
  - Feed page — between card rows, visible to all users (guests + signed-in)
  - Summary / Simplify pages — between generated content and bottom buttons, signed-in users only (these pages are auth-gated)
- **Until real ads are live:** ad slot shows a self-promotion unit — "Know an engineer who'd love this? Share it." Turns dead space into a word-of-mouth nudge.
- **Why ads for signed-in users too:** product is free, no double-dipping concern. EthicalAds units are clean and developer-relevant — they do not degrade the experience.

---

## User Feedback

- Signed-in users only
- **Card** — "⚑ Report incorrect tags, prerequisites" button below tags/prerequisites chips, above action buttons. Opens a modal with two optional fields: Suggested Tags and Suggested Prerequisites (comma-separated).
- **Summary / Simplify pages** — "⚑ Report incorrect summary / simplification" link below content body, above bottom buttons. Opens a modal with one field: describe what's wrong.
- A row is only submitted if the field has content — empty fields are skipped.
- Rate limit: 5 submissions per user per day. Exceeding returns a message: "You've reached the feedback limit for today. Try again tomorrow."
- Review is manual by admin — no auto-apply of suggestions.

---

## Non-Signed-In Button Behavior
- Summary and Simplify buttons visible but locked — on click: show "Sign in with Google" modal
- Tags and prerequisites hidden from non-signed-in users

## Initial Blog Scope
- 15–25 curated company blogs

## RSS Polling
- Once per day is sufficient — most feeds post every 2–5 days at most

## Tech Stack
- FastAPI + Alpine.js

## Verified RSS Feeds (v1)

> **Note:** None of the feeds have a dedicated `<tags>` field. Classification metadata is available only via `<category>` field where present.

| Blog | Full Content | Categories in Feed | Thumbnail |
|------|-------------|-------------------|-----------|
| Cloudflare | Yes | Yes | No |
| GitHub | Yes | Yes | No |
| Meta | Yes | Yes | No |
| AWS | Yes | Yes | No |
| Slack Engineering | Yes | Yes | No |
| Netflix (via Medium) | Yes | Yes | No |
| Airbnb (via Medium) | Yes | Yes | No |
| Dropbox | Yes | Yes | No |
| Fly.io | Yes | No | Yes |
| Discord | No | No | Yes |
| Spotify | No | Yes | No |
| Google Developers | No | No | No |
| Stripe | No | No | No |
