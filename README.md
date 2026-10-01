# Dota 2 MMR shift

A static page of OpenDota public-profile rank counts, showing how the medal
ladder moved after lower-rank wins started paying about +35 to +40 MMR in
June 2026. Live fetch on load; daily snapshots in this repo.

## Data

`data/opendota.json` — snapshots of
`https://api.opendota.com/api/distributions`. Seeded with Wayback captures
(2024-08-05, 2024-08-22, 2025-01-25, 2026-08-02) plus captures from 2026-09-30
onward. A GitHub Action appends one row per day. There is no snapshot for
June or July 2026; day-to-day change starts when consecutive daily snapshots
exist.

OpenDota free API: 60 calls/minute, 3,000/day, no key. This page makes one
call per load; the cron makes one call per day.

## Cron

`.github/workflows/snapshot.yml` runs `scripts/snapshot.py` daily at 06:00 UTC.

## Hosting

GitHub Pages from `main`. Locally: `python -m http.server 8765`.
