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