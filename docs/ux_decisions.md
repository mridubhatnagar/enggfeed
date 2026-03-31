# UX Decisions: Engineering Blog Aggregator

## Navbar
- Guest: Logo on left, Sign In button on right
- Signed-in: Logo on left, avatar (initials fallback), user name, Sign Out on right

## Colors
- Brand/accent color: `#4F46E5` (Electric Indigo)
- Tags: rectangular, dark background with white text
- Prerequisites: rectangular, solid background — color TBD. Both tags and prerequisites will be solid with different colors; finalize during frontend development when colors can be compared visually.
- Button colors: TBD — to be finalized during frontend development when colors can be visually reviewed

## Company Filter
- Dropdown (v1)
- Rich styling: company favicon/logo next to each company name, smooth open/close animation, highlighted selected state

## Feed Page Layout
- Desktop: 3 column card grid throughout — default feed and tag filter use the same grid layout
- Mobile: single column vertical list
- Company filter dropdown above the grid
- **Future consideration:** grid/list toggle for users — purely a CSS change, low effort when needed

## Card Layout
- Thumbnail (clickable)
  - Company name badge overlaid at bottom-left of thumbnail — `#4F46E5` background, white text
  - **Note:** Verify visually during frontend development — may need position adjustment if it clashes with tags/buttons below
- Title (clickable)
- Prerequisites — shown above tags, signed-in users only (Partial + Full tier), max 3 chips visible, "+N more" if exceeds. Clicking a chip opens the prerequisite modal.
- Tags — shown below prerequisites, signed-in users only, max 3 visible, "+N more" if exceeds
- Summary + Simplify buttons
- ↗ signal on card to indicate clicking opens in new tab

## Card Behavior
- Clicking card (thumbnail or title) = Full Read — opens original article in new tab
- Summary button → opens dedicated Summary page within platform
- Simplify button → opens dedicated Simplify page within platform
- Summary + Simplify visible but locked for guests — clicking shows "Sign in with Google" modal
- **Content tier behavior:**
  - Limited tier: Summary + Simplify buttons hidden, only Full Read available
  - Partial tier: Summary visible, Simplify hidden
  - Full tier: all buttons visible

## Summary / Simplify Page Layout
> **Note:** Summary and Simplify are two separate pages with separate endpoints. They share the same layout structure but are independent from each other.

- Thumbnail
- Title
- Attribution line:
  - Summary page: "Original blog is by **[Company Name]**. You are seeing an AI generated summary of the original blog published on **[date]**."
  - Simplify page: "Original blog is by **[Company Name]**. You are seeing an AI generated simplified explanation of the original blog published on **[date]**."
- Summary/Simplify last updated date shown separately on the page
- Prerequisites just below title (signed-in users only, Partial + Full tier, clickable chips — opens prerequisite modal). All prerequisites shown — no truncation.
- Tags just below prerequisites (signed-in users only, clickable — navigates back to feed filtered by that tag). All tags shown — no truncation.
- Generated content below (spinner shown on first request and on first request after 7-day refresh — all other requests served from cache/DB instantly)
- **Conditional rendering:** For summary, `short_summary` and each `key_points` item are only rendered if non-empty. For simplify, `simplify` content is only rendered if non-empty. Empty fields are silently skipped.
- Summary/Simplify page only loads when data is successfully available
- On error: user stays on main feed, flash message shown just below navbar — "Sorry, we are unable to process your request. Please try again after some time."
- On error: user stays on main feed, flash message shown just below navbar
- Bottom buttons:
  - **Summary page**: ← Back | Read Original ↗ | Simplify (hidden for Partial tier articles — ELI5 not available)
  - **Simplify page**: ← Back | Read Original ↗ | Summary

## Prerequisites Modal
- Opens when a signed-in user clicks a prerequisite chip on a card
- No page navigation — everything happens in the modal
- **Structure:**
  - Topic name as modal title
  - **Primer** (default view):
    - 1-2 line definition
    - "Why it matters" — left-border accented block
    - "Example" — left-border accented block
  - **"Read more"** button reveals the Deep dive section
  - **Deep dive** — detailed technical explanation
- Clicking outside the modal or pressing Esc closes it
- **Conditional rendering:** Each section (`definition`, `why_it_matters`, `example`, `deep_dive`) is only rendered if the value is non-empty. If a field is missing or empty, that section is silently skipped — no empty blocks shown.
- **v2:** Depth and structure of prerequisite content (primer length, deep dive detail level) to be revisited after seeing how users interact with it in v1

## Tags
- Hidden from non-signed-in users on both feed cards and summary/simplify pages
- Clickable — filters feed in place, URL updates (e.g., `/?tag=databases`) for shareability

## Limited Content Badge
- Appears in the same position as tags on the card
- Mutually exclusive with tags and prerequisites — if Limited badge is shown, no tags or prerequisites are shown

## Sign In Modal
- Product logo
- Punchy tagline
- "Sign in with Google" button

## Empty States
- Show an illustration with "No results found" text
- "Clear Filters" button — resets all active filters/search and returns to full default feed
- **Note:** Find free illustrations for empty state (e.g., unDraw, Storyset)

## Pagination
- Pagination over infinite scroll — users come to read and discover, not endlessly scroll
- Page state reflected in URL (e.g., `/?page=2&tag=databases`) for shareability
- **Note:** Articles per page to be decided during frontend development — depends on card size and screen size

## Ad Slots
- **Feed page** — full-width ad strip between card rows (after row 1). Visible to all users.
- **Summary / Simplify pages** — ad unit between generated content and bottom buttons. Signed-in users only (pages are auth-gated).
- **Placeholder copy** (until real ads are live): self-promotion — "Know an engineer who'd love this? Share it." / "Found this summary useful? Share it."
- Ad units are labeled "Sponsored" when real ads are active. No label on self-promotion placeholder.

