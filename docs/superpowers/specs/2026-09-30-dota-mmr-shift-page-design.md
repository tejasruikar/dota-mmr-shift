# Dota 2 MMR shift page — design

Date: 2026-09-30

## Purpose

A single static web page, hosted on GitHub Pages, that shows how the Dota 2 ranked
medal distribution has moved since Valve changed lower-rank MMR gains in June 2026
(wins about +35 to +40, losses about −25 below roughly 4k MMR). The page is meant to
be linked from Reddit: it opens fast, needs no login, and every number on it names
its source.

The headline question it answers: how many players were in Crusader, Archon, and
Legend before the change, and how many are there now.

## Data sources

### Stratz percentiles (primary series)

Esports Tales publishes a table roughly every two months giving, for each medal and
star, the cumulative percentile of calibrated accounts at or below that rank, sourced
from Stratz. Series covers Season 6 (May 2023 onward). The March–July 2024 tables were
OpenDota-sourced and are excluded so the series is one population throughout.

Stratz has no public endpoint for this. The tables are transcribed by hand into
`data/stratz.json`. A new entry is one JSON object appended when a new table is
published.

Medal share for a month = cumulative percentile at star 5 of that medal minus the
cumulative percentile at star 5 of the medal below (Herald uses 0 as its floor;
Immortal = 100 − Divine 5). Star share is the difference between adjacent stars.

Player counts = share × an assumed population. Default 7,000,000, the sample size
Esports Tales cites for Season 6. The population is a user-editable field. The page
states plainly that percentages are the measurement and counts are scaled.

### OpenDota `/api/distributions` (secondary series)

Live, keyless, CORS-enabled. Returns absolute counts per rank tier bin for public
profiles OpenDota has seen. This is a different population (hidden profiles missing,
inactive accounts retained), so it is never spliced into the Stratz series. It is
shown as its own thing: a live "today" bar, and a trend once snapshots accumulate.

OpenDota recomputes the distribution daily (confirmed: every bin changed between
2026-09-30 and 2026-10-01). Snapshots are appended daily to `data/opendota.json` by a
GitHub Actions cron.

The file is seeded with the snapshots that exist before the cron starts: Wayback
Machine captures of the endpoint on 2024-08-05, 2024-08-22, 2025-01-25, and
2026-08-02, plus direct captures on 2026-09-30 and 2026-10-01. The 2023-02-01 capture
is excluded (pre-Glicko matchmaking). There is no OpenDota data between June and
August 2026; that gap cannot be reconstructed from any source.

Resolution, stated on the page: Stratz is bi-monthly; OpenDota is daily from October
2026 onward with sparse points before that.

## Repository layout

```
dota-mmr-shift/
  index.html                       the whole page: markup, CSS, JS, inline SVG charts
  data/stratz.json                 hand-maintained percentile tables
  data/opendota.json               cron-appended snapshots (starts as [])
  scripts/snapshot.py              fetch OpenDota, append to data/opendota.json
  tests/test_snapshot.py           unit tests for the append logic
  .github/workflows/snapshot.yml   weekly cron; runs the script; commits if changed
  README.md                        how to add a Stratz row, how the cron works, how to fork
  docs/superpowers/specs/          this document
  docs/superpowers/plans/          implementation plan
```

No build step. No npm. No framework. `index.html` is served as-is by GitHub Pages
from `main`.

## Data formats

### `data/stratz.json`

```json
{
  "source": "Esports Tales / Stratz",
  "source_url": "https://www.esportstales.com/dota-2/seasonal-rank-distribution-and-mmr-medals",
  "default_population": 7000000,
  "events": [
    { "date": "2026-06-18", "label": "Lower-rank win gains raised (+35 to +40 vs −25)" }
  ],
  "months": [
    {
      "month": "2026-08",
      "published": "2026-08-04",
      "cumulative": {
        "herald":   [0.23, 3.10, 5.89, 8.94, 12.23],
        "guardian": [15.80, 19.50, 23.29, 27.12, 30.99],
        "crusader": [35.02, 39.04, 43.00, 46.90, 50.70],
        "archon":   [54.54, 58.21, 61.72, 65.03, 68.16],
        "legend":   [71.31, 74.18, 76.81, 79.22, 81.44],
        "ancient":  [83.65, 85.59, 87.28, 88.76, 90.06],
        "divine":   [91.55, 92.83, 93.88, 94.75, 95.56],
        "immortal": [99.99]
      }
    }
  ]
}
```

Each medal array is stars 1–5 in order; Immortal has one value. `months` is sorted
ascending by `month`. The page derives shares and counts from `cumulative`; nothing
derived is stored.

### `data/opendota.json`

```json
[
  {
    "date": "2026-10-05",
    "total": 8615104,
    "bins": { "11": 9448, "12": 155196, "13": 164981, "80": 342546 }
  }
]
```

`bins` holds every bin the API returns (36 keys in practice; the example is
abbreviated). Keys are OpenDota `rank_tier` values (tens digit = medal 1–8, ones
digit = star 1–5; `80` is Immortal). The script stores the raw bins; the page
derives medal totals. One entry per calendar date, sorted ascending; a rerun on the
same date is a no-op. Seeded entries carry an extra `"source": "wayback"` or
`"source": "manual"` field; cron entries carry none.

## Page

Order, top to bottom. Every chart has a title naming the metric, axis labels with
units, a legend when more than one series is drawn, and a caption naming source and
time range.

1. **Headline.** Three cards: Crusader, Archon, Legend. Each shows players in the
   bracket in June 2026 (last table before the change) and in the latest month, the
   difference, and the share percentages. A population input (default 7,000,000)
   sits beside them; editing it recomputes every count on the page. The latest month
   is whichever entry in `stratz.json` is last. Below the cards, a table of all
   eight medals with the same columns (June share and count, latest share and count,
   change in count and in share points), Crusader/Archon/Legend rows highlighted.

1b. **Change by bracket (OpenDota, live).** On load the page fetches
   `/api/distributions` and treats it as "now". A table of all eight medals, with a
   toggle to 36 stars, shows: current count and share; then change in count and in
   share points over 1 day, 7 days, 30 days, since 2026-08-02 (earliest post-change
   OpenDota point), and since 2025-01-25 (pre-change).    Each period column uses the
   latest committed snapshot dated at or before `today − N days` (or the named date).
   For the day-based periods the snapshot must also be within a tolerance of the
   target (1 day: 1; 7 days: 3; 30 days: 7) so a column is never labeled "7 days"
   while actually comparing against a months-old point. A column with no qualifying
   snapshot is omitted entirely. Column headers show the actual baseline date. Positive deltas green,
   negative red. If the live fetch fails, the latest committed snapshot is "now" and
   the caption says so. If there is no snapshot at all, the section is omitted.
   Below the table, once seven or more snapshots exist, one small sparkline per
   medal of share over snapshot dates; hidden until then.

2. **Timeline.** A range slider over the published months plus a play button that
   steps through them at about one month per 700 ms. Below it, a bar chart of medal
   share that animates between months. A toggle switches between 8 medal bars and 36
   star bars. A vertical marker labels the June 2026 change on the slider track.
   The current month is written into the URL as `?month=YYYY-MM` so a shared link
   opens on that frame; the play button does not rewrite the URL while playing.

3. **Trend.** Line chart of Crusader, Archon, and Legend share across the whole
   series, with the June 2026 event marked. Hovering a point shows the month, share,
   and scaled count.

4. **OpenDota charts.** Using the same live fetch as 1b: a bar of medal share for
   "public profiles, today" with the total profile count and a one-line note that
   this is a different population. If `data/opendota.json` has two or more
   snapshots, a line chart shows Crusader, Archon, Legend share by snapshot date
   (x positions proportional to date, since the seed points are years apart and the
   cron points are a day apart). If the fetch fails, the today bar is omitted. If
   there are fewer than two snapshots, the trend is omitted. Nothing renders empty.

5. **Break-even.** Two sliders, win gain (20–45) and loss (20–30), defaults 35 and 25.
   Shows the win rate that holds MMR (`loss / (gain + loss)`) and the MMR drift over
   100 games at 45% and 50% win rate.

6. **Method and sources.** Short paragraphs: how medal share is computed, why counts
   are scaled, why OpenDota is kept separate, the excluded 2024 months, the
   resolution limits (Stratz bi-monthly; OpenDota daily from October 2026, sparse
   before; June–August 2026 gap), links to Esports Tales, OpenDota, the Wayback
   captures, and the Reddit threads where the change was first reported.

Sharing: Open Graph and Twitter card meta tags (title, description, and a static
`og-image.png` committed to the repo); a copy-link button that copies the current
URL including `?month=`.

Styling: one dark theme, system font stack, no external CSS or fonts. Works at 360px
width; charts are SVG with `viewBox` so they scale.

## Automation

`scripts/snapshot.py`:

- `fetch()` GETs `https://api.opendota.com/api/distributions` with a 30 s timeout and
  a `User-Agent` header. Returns the parsed `ranks.rows` and `ranks.sum.count`.
- `to_entry(rows, total, date)` builds one `data/opendota.json` entry.
- `append(entries, entry)` returns a new list with `entry` added and sorted by `date`,
  unless an entry with the same `date` exists, in which case the list is returned
  unchanged.
- `main()` reads `data/opendota.json`, fetches, appends for today's UTC date, writes
  back with two-space indentation, exits 0. Any network or parse failure exits 1
  with the error on stderr; the file is not touched.

`.github/workflows/snapshot.yml`: `schedule: cron "0 6 * * *"` (daily 06:00 UTC)
plus `workflow_dispatch`. Steps: checkout, setup Python 3.12, run the script, commit
and push only if `git diff --quiet -- data/opendota.json` fails. Uses the default
`GITHUB_TOKEN` with `contents: write`.

Hosting: GitHub Pages, source `main`, folder `/`. Each push redeploys.

## Testing

- `tests/test_snapshot.py` (`unittest`, stdlib): `to_entry` produces the expected
  shape from a captured sample response; `append` adds a new date and keeps the list
  sorted; `append` is a no-op for a duplicate date; `main` leaves the file untouched
  when `fetch` raises (monkeypatched).
- `tests/test_data.py` also checks `data/opendota.json`: sorted unique dates, every
  entry has 36 bins summing to `total`, and the seed dates are present.
- Delta logic in the page is pure functions (`snapshotAtOrBefore(snaps, isoDate)`,
  `medalCounts(bins)`) checked in the browser against hand-computed values from the
  2026-08-02 and 2026-09-30 seeds: Legend count 1,232,444 → 1,425,703 (delta
  +193,259); Herald count 865,841 → 743,294 (delta −122,547).
- Page: opened in the Cursor browser against a local static server. Checks: headline
  counts match a hand calculation for June and August 2026; slider and `?month=`
  round-trip; play runs to the end and stops; OpenDota section appears with live data
  and disappears when the fetch is blocked; break-even values for 35/25 and 40/25
  are 41.7% and 38.5%; nothing renders empty when `data/opendota.json` is `[]`.

## Out of scope

- Fetching Stratz directly.
- Per-player match histories or measured per-game MMR deltas.
- Simulation or projection of the future distribution.
- Region or role breakdowns.
- Any server, database, or login.
