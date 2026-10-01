# Dota 2 MMR shift

A static page showing how Dota 2 medal populations moved after Valve raised
lower-rank MMR gains in June 2026 (wins about +35 to +40, losses about −25 below
roughly 4k MMR). Built to be linked from Reddit.

## Data

- `data/stratz.json` — cumulative percentile per medal and star, one entry per
  month, transcribed from the Esports Tales tables
  (https://www.esportstales.com/dota-2/seasonal-rank-distribution-and-mmr-medals),
  which are sourced from Stratz. Season 6 only; March–July 2024 excluded because
  those tables were OpenDota-based.
- `data/opendota.json` — daily snapshots of `https://api.opendota.com/api/distributions`
  (public profiles only), appended by GitHub Actions. Seeded with Wayback Machine
  captures from 2024-08-05, 2024-08-22, 2025-01-25, and 2026-08-02 plus direct
  captures from 2026-09-30 and 2026-10-01. There is no data for June–July 2026.
  A different population from Stratz, so it is charted separately.

Medal share = star-5 cumulative of the medal − star-5 cumulative of the medal below.
Player counts on the page are share × an editable population (default 7,000,000).

## Adding a new Stratz month

When Esports Tales publishes a new table, append one object to `months` in
`data/stratz.json`:

```json
{ "month": "2026-10", "published": "2026-10-03", "cumulative": {
  "herald": [h1, h2, h3, h4, h5],
  "guardian": [...], "crusader": [...], "archon": [...],
  "legend": [...], "ancient": [...], "divine": [...],
  "immortal": [99.99] } }
```

Then run `python -m unittest discover -s tests -v` (checks ordering and that all
36 values increase) and push. The page picks up the new month as "latest".

## OpenDota cron

`.github/workflows/snapshot.yml` runs `scripts/snapshot.py` daily at 06:00 UTC and
commits `data/opendota.json` if a new date was added. Trigger it by hand from the
Actions tab ("Run workflow"). The page's change-by-bracket table computes 1-day,
7-day, and 30-day deltas from these snapshots; the 7- and 30-day columns appear once
snapshots that old exist.

## Hosting

GitHub Pages, source `main`, folder `/`. Every push redeploys. To run locally:

```
python -m http.server 8765
```

then open http://localhost:8765/.

## Forking

Fork, enable Pages on your fork, and update the `og:url` and `og:image` meta tags
in `index.html` to your Pages URL.
