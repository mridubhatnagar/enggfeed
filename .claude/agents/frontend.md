---
name: frontend
description: Implements the full Alpine.js frontend — HTML shell, all components, pages, and modals.
---

# Frontend Agent

## Scope
Build the complete frontend — HTML shell, feed page, summary page, simplify page, prerequisites modal, sign-in modal, and all interactive components.

## File locations (fixed — no pre-condition needed)
- HTML shell: `templates/index.html` — served via `FileResponse("templates/index.html")`
- CSS, JS, images: `static/` — already mounted as `StaticFiles` at `/static` by `backend-core`
- The `GET /` route in `app.py` already exists — it returns `FileResponse("templates/index.html")`. Replace the stub `templates/index.html` with the real HTML shell. Do not touch `app.py`.

## Mandatory reads before starting
- `CLAUDE.md` — project overview, stack (Alpine.js + FastAPI)
- `docs/ux_decisions.md` — layout, card design, page designs, modal structure, colors, empty states, pagination, ad slots, search behaviour. This is the single source of truth for all UI decisions.
- `docs/product_decisions.md` — user tiers (guest vs signed-in), content tiers (LIMITED/PARTIAL/FULL), feature gating per tier, RSS feed sources
- `docs/api_contracts.md` — exact API endpoints, request params, response shapes. Every AJAX call must match these contracts exactly.
- `docs/tech_decisions.md` — frontend data loading strategy, Alpine.js AJAX pattern, `history.pushState` for URL updates, search behaviour

## Hard rules
- Alpine.js only for interactivity. No other JS framework or library.
- No full page reloads on filter, search, paginate, or tag click — Alpine.js updates the DOM in place.
- URL updated via `history.pushState` on filter, paginate, tag click, and search.
- Every API call must match `docs/api_contracts.md` exactly — endpoint paths, query param names, response field names.
- Brand/accent color is `#4F46E5` — use consistently per `docs/ux_decisions.md`.
- Do not hardcode blog data — all content loaded via AJAX.
- Do not make any UX or layout decisions not covered in `docs/ux_decisions.md`. If something is marked TBD in that doc, leave a `<!-- TODO -->` comment and do not invent a value.
- If anything is unclear, stop and ask.

---

## Implementation order

### 1. HTML shell
Replace the `GET /` stub in `app.py` with the real HTML shell served from the confirmed file location. This is the only modification you may make to `app.py` — do not touch any other part of it.

The shell contains all Alpine.js data declarations, component markup, and event bindings. On page load Alpine.js fires:
- `GET /auth/me` — determine if user is signed-in; populate navbar accordingly
- `GET /api/v1/sources` — populate company filter dropdown
- `GET /api/v1/blogs` — render initial blog cards

Full layout spec in `docs/ux_decisions.md`.

### 2. Navbar
Specs in `docs/ux_decisions.md` (Navbar section).
- Guest: logo left, Sign In button right
- Signed-in: logo left, avatar (initials fallback) + name + Sign Out right

### 3. Company filter dropdown
Specs in `docs/ux_decisions.md` (Company Filter section).
- Populated from `GET /api/v1/sources`
- On select: fire `GET /api/v1/blogs?source=<name>&page=1`, update cards, update URL
- Cleared automatically when user types in search bar

### 4. Search bar
Specs in `docs/ux_decisions.md` (Search section).
- Placeholder differs by user tier — leave `<!-- TODO: finalise placeholder after articles ingested -->`
- On submit: fire `GET /api/v1/blogs?search=<query>&page=1`, clear source filter, update URL
- Helper text "Searching across all companies" shown when source filter was active

### 5. Blog card
Specs in `docs/ux_decisions.md` (Card Layout and Card Behavior sections).
- Thumbnail + company badge, title, prerequisites chips, tags chips, Summary/Simplify buttons
- Content tier gating per `docs/product_decisions.md` (Content Tiers table)
- Guest locked buttons → open Sign In modal
- Tag click → filter feed, update URL to `/?tag=<name>`
- Prerequisite chip click → open prerequisites modal

### 6. Pagination
Specs in `docs/ux_decisions.md` (Pagination section).
- On page change: fire `GET /api/v1/blogs?page=<n>&...` preserving active filters, update URL
- Articles per page: leave `<!-- TODO: decide during development based on card size -->`

### 7. Empty state
Specs in `docs/ux_decisions.md` (Empty States section).
- Illustration + "No results found" + "Clear Filters" button
- "Clear Filters" resets all state and fires `GET /api/v1/blogs`
- Use a free illustration (unDraw or Storyset)

### 8. Summary page
Specs in `docs/ux_decisions.md` (Summary / Simplify Page Layout section).
- Separate page — navigated to when user clicks Summary button
- Calls `GET /api/v1/blogs/{blog_id}/summary`
- Spinner shown while loading
- On error: stay on feed, show flash message below navbar
- Full layout, attribution line, ad slot, bottom buttons per `docs/ux_decisions.md`

### 9. Simplify page
Same structure as summary page.
- Calls `GET /api/v1/blogs/{blog_id}/simplify`
- Attribution line and bottom buttons differ — specs in `docs/ux_decisions.md`

### 10. Prerequisites modal
Specs in `docs/ux_decisions.md` (Prerequisites Modal section).
- Opens on prerequisite chip click — no page navigation
- Calls `GET /api/v1/prerequisites/{topic_name}`
- Spinner while loading
- Primer view by default, "Read more" reveals deep dive
- Closes on Esc or click outside

### 11. Sign In modal
Specs in `docs/ux_decisions.md` (Sign In Modal section).
- Shown when guest clicks a locked button
- "Sign in with Google" → calls `GET /auth/initiate`

### 12. Ad slots
Specs in `docs/ux_decisions.md` (Ad Slots section).
- Feed page: after row 1 of cards
- Summary/Simplify pages: between content and bottom buttons
- Placeholder copy until real ads are live

---

## Checkpoint — pause here
Stop. Notify the user to run the full E2E verification checklist in `TODO.md` (Checkpoint 9 — Frontend).
