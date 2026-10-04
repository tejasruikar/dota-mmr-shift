# Dota 2 MMR shift

A static page of OpenDota public-profile rank counts, showing how the medal
ladder moved after lower-rank wins started paying about +35 to +40 MMR in
June 2026. The page only reads `data/opendota.json`. Visitors do not call
OpenDota.

## Data

`data/opendota.json` — snapshots of
`https://api.opendota.com/api/distributions`. Seeded with Wayback captures
(2024-08-05, 2024-08-22, 2025-01-25, 2026-08-02) plus captures from 2026-09-30
onward. A GitHub Action refreshes today's row and appends a new one at UTC
midnight. There is no snapshot for June or July 2026; day-to-day change starts
when consecutive daily snapshots exist.

OpenDota free API: 60 calls/minute, 3,000/day, no key. This project uses one
call per cron run. GitHub Actions will not run a workflow more often than every
5 minutes, so the job is `*/5 * * * *` (288 calls/day).

## Cron

`.github/workflows/snapshot.yml` runs `scripts/snapshot.py` every 5 minutes.
Same-day runs replace that date's counts if OpenDota moved; unchanged numbers
are a no-op and do not commit.

## Hosting

GitHub Pages from `main`. Locally: `python -m http.server 8765`.
