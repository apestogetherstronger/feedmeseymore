# Feed Me, Seymore 🌱

A finite, intentional feed for content already captured in the Trello Learn system.

## Philosophy

This is not another recommendation engine. The feed ends. It is optimized for **worth my attention now**, not time-on-site.

## Workflow

1. Discover/save content normally (YouTube, X, web, etc.).
2. Trello remains the source of truth for curation.
3. `feed.json` is generated from worthwhile unconsumed Learn items and ranked using the Learn recommendation model.
4. Open the original content from the feed.
5. Use the Trello deep link to record the outcome:
   - consumed: archive the Trello card (positive signal)
   - not interested: move it to `Learn · Skipped` (negative signal)
   - durable reference: move it to `Learn · Reference`

The page deliberately has no infinite-scroll content generation.

## Publishing

GitHub Pages should serve the repository root from the `main` branch. The daily curator updates `feed.json`; the UI itself normally does not need rebuilding.

## Automated feed refresh

Publishing is handled by GitHub Actions via `.github/workflows/feed-refresh.yml`.
The workflow is scheduled hourly but executes the refresh only at
`00:00, 04:00, 08:00, 12:00, 16:00, 20:00` in `Asia/Jerusalem`. This
keeps the schedule correct across Israeli daylight-saving changes. It can also
be run manually with **Run workflow**.

The refresh is deterministic and does **not** discover or enrich content. It:

1. Checks that the canonical Trello automation card is Active.
2. Reads open `Learn · Enriched`, `Learn · Recommended`, and `Learn · Inbox`.
3. Reconciles the complete eligible Trello set into `feed.json` by stable Trello shortlink.
4. Commits and pushes `feed.json`.
5. Fetches the published file back from GitHub and verifies it.
6. Adds one compact line to the dedicated Trello automation log.

### Required GitHub Actions secrets

Create these repository secrets under **Settings → Secrets and variables → Actions**:

- `TRELLO_API_KEY`
- `TRELLO_TOKEN`

No GitHub PAT is required; the workflow uses the built-in `GITHUB_TOKEN` with
`contents: write`.

The Trello card/list IDs are non-secret environment values in the workflow and
only need changing if the board structure changes:
`TRELLO_CANONICAL_CARD_ID`, `TRELLO_ENRICHED_LIST_ID`,
`TRELLO_RECOMMENDED_LIST_ID`, `TRELLO_INBOX_LIST_ID`, `TRELLO_LOG_CARD_ID`,
and `TRELLO_LOG_POLICY_CARD_ID`.

