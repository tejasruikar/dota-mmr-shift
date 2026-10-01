# Dota 2 MMR Shift Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single static page on GitHub Pages showing how Dota 2 medal populations (Crusader, Archon, Legend in particular) moved after the June 2026 lower-rank MMR gain change, with hand-maintained Stratz history, cron-snapshotted OpenDota history, and a live OpenDota bar.

**Architecture:** One `index.html` (vanilla JS, CSS, HTML bar charts, inline SVG line charts) reads `data/stratz.json` and `data/opendota.json` from the same origin and fetches OpenDota live. A stdlib Python script appends weekly OpenDota snapshots from a GitHub Actions cron. No build step.

**Tech Stack:** HTML/CSS/vanilla JS (ES2020), Python 3.12 stdlib (`unittest`, `urllib`), GitHub Actions, GitHub Pages, Pillow only for the one-off OG image.

Spec: `docs/superpowers/specs/2026-09-30-dota-mmr-shift-page-design.md`.

## Global Constraints

- Repo root: `C:\Users\Tejas\dota-mmr-shift`. All paths below are relative to it. Shell is PowerShell.
- No npm, no framework, no build step, no external CSS or fonts. `index.html` is served as-is.
- Python: stdlib only in `scripts/snapshot.py` and tests. Run tests with `python -m unittest discover -s tests -v`.
- Stratz series excludes March–July 2024 (OpenDota-sourced months).
- Medal share = star-5 cumulative of the medal minus star-5 cumulative of the medal below; Herald floor is 0; Immortal = 100 − Divine 5.
- Counts = share × population; default population 7,000,000; population is user-editable.
- OpenDota data is never merged into the Stratz series; it gets its own charts.
- OpenDota cron runs daily (`0 6 * * *`). `data/opendota.json` is seeded with six snapshots: Wayback captures 2024-08-05, 2024-08-22, 2025-01-25, 2026-08-02 (`"source": "wayback"`) and direct captures 2026-09-30, 2026-10-01 (`"source": "manual"`). Entries sorted by date.
- Change-by-bracket periods: 1 day, 7 days, 30 days, since 2026-08-02, since 2025-01-25. A period uses the latest snapshot dated at or before the target; with none, the column is omitted.
- Nothing renders empty: sections without data stay hidden.
- Baseline month for "before" is `2026-06`. "Latest" is the last entry in `stratz.json`.
- Event marker: `2026-06-18`, label "Lower-rank win gains raised (+35 to +40 vs −25)".
- Charts: title naming the metric, axis labels with units, legend when 2+ series, caption with source and time range.
- Commit after every task with the message given.

---

### Task 1: Data files and data validation test

**Files:**
- Create: `data/stratz.json`
- Create: `data/opendota.json`
- Create: `.gitignore`
- Test: `tests/test_data.py`

**Interfaces:**
- Produces: `data/stratz.json` with shape `{source, source_url, default_population, events:[{date,label}], months:[{month:"YYYY-MM", published?: "YYYY-MM-DD", cumulative:{herald:[5], guardian:[5], crusader:[5], archon:[5], legend:[5], ancient:[5], divine:[5], immortal:[1]}}]}`, months ascending. `data/opendota.json` is `[]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_data.py`:

```python
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDALS = ["herald", "guardian", "crusader", "archon", "legend", "ancient", "divine", "immortal"]
EXCLUDED_2024 = {"2024-03", "2024-04", "2024-05", "2024-06", "2024-07"}


class StratzDataTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data" / "stratz.json").read_text(encoding="utf-8"))

    def test_top_level_fields(self):
        self.assertEqual(self.data["default_population"], 7000000)
        self.assertEqual(self.data["events"][0]["date"], "2026-06-18")
        self.assertTrue(self.data["source_url"].startswith("https://"))

    def test_months_sorted_and_unique(self):
        months = [m["month"] for m in self.data["months"]]
        self.assertEqual(months, sorted(months))
        self.assertEqual(len(months), len(set(months)))
        self.assertFalse(set(months) & EXCLUDED_2024)

    def test_baseline_and_latest_present(self):
        months = [m["month"] for m in self.data["months"]]
        self.assertIn("2026-06", months)
        self.assertEqual(months[-1], "2026-08")

    def test_each_month_has_36_strictly_increasing_values(self):
        for m in self.data["months"]:
            c = m["cumulative"]
            flat = []
            for medal in MEDALS[:-1]:
                self.assertEqual(len(c[medal]), 5, f'{m["month"]} {medal}')
                flat += c[medal]
            self.assertEqual(len(c["immortal"]), 1, m["month"])
            flat += c["immortal"]
            self.assertEqual(len(flat), 36, m["month"])
            for a, b in zip(flat, flat[1:]):
                self.assertLess(a, b, f'{m["month"]}: {a} is not below {b}')
            self.assertLessEqual(flat[-1], 100)


class OpenDotaDataTest(unittest.TestCase):
    SEED_DATES = ["2024-08-05", "2024-08-22", "2025-01-25", "2026-08-02", "2026-09-30", "2026-10-01"]

    def setUp(self):
        self.data = json.loads((ROOT / "data" / "opendota.json").read_text(encoding="utf-8"))

    def test_is_sorted_unique_list(self):
        self.assertIsInstance(self.data, list)
        dates = [e["date"] for e in self.data]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(len(dates), len(set(dates)))

    def test_seed_dates_present(self):
        dates = [e["date"] for e in self.data]
        for d in self.SEED_DATES:
            self.assertIn(d, dates)

    def test_each_entry_has_36_bins_summing_to_total(self):
        for e in self.data:
            self.assertEqual(len(e["bins"]), 36, e["date"])
            self.assertEqual(sum(e["bins"].values()), e["total"], e["date"])
            self.assertEqual(sorted(e["bins"]), sorted(f"{m}{s}" for m in range(1, 8) for s in range(1, 6)) + ["80"], e["date"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v`
Expected: errors with `FileNotFoundError` for `data\stratz.json`.

- [ ] **Step 3: Create `.gitignore`, `data/opendota.json`, `data/stratz.json`**

`.gitignore`:

```
__pycache__/
.venv/
```

`data/opendota.json` (six seed snapshots; bins are OpenDota `rank_tier` counts, verified to sum to `total`):

```json
[
  {"date": "2024-08-05", "source": "wayback", "total": 5626749, "bins": {"11": 3503, "12": 70260, "13": 80778, "14": 105269, "15": 121375, "21": 138666, "22": 153517, "23": 170509, "24": 185419, "25": 200465, "31": 221113, "32": 231754, "33": 241372, "34": 249072, "35": 251818, "41": 261953, "42": 255719, "43": 249441, "44": 238523, "45": 227039, "51": 227676, "52": 205641, "53": 185906, "54": 168705, "55": 151911, "61": 149272, "62": 127067, "63": 107863, "64": 90810, "65": 79877, "71": 92596, "72": 75556, "73": 59486, "74": 46293, "75": 40787, "80": 159738}},
  {"date": "2024-08-22", "source": "wayback", "total": 5644375, "bins": {"11": 3538, "12": 70883, "13": 81346, "14": 105823, "15": 121799, "21": 139204, "22": 154059, "23": 170905, "24": 185822, "25": 201157, "31": 221163, "32": 232103, "33": 241373, "34": 248935, "35": 251880, "41": 261868, "42": 255591, "43": 249367, "44": 238485, "45": 227299, "51": 227812, "52": 206185, "53": 186454, "54": 168905, "55": 152315, "61": 150240, "62": 127597, "63": 108091, "64": 91480, "65": 80798, "71": 93414, "72": 76264, "73": 60172, "74": 46853, "75": 41405, "80": 163790}},
  {"date": "2025-01-25", "source": "wayback", "total": 5795487, "bins": {"11": 3876, "12": 76254, "13": 86330, "14": 110657, "15": 127261, "21": 144650, "22": 159846, "23": 176115, "24": 189893, "25": 204815, "31": 224294, "32": 234290, "33": 242718, "34": 250412, "35": 252527, "41": 262288, "42": 256803, "43": 249711, "44": 239331, "45": 228846, "51": 229288, "52": 208857, "53": 189664, "54": 171785, "55": 156216, "61": 154483, "62": 132177, "63": 112851, "64": 95745, "65": 85264, "71": 99066, "72": 82075, "73": 65420, "74": 51158, "75": 46389, "80": 194132}},
  {"date": "2026-08-02", "source": "wayback", "total": 8380687, "bins": {"11": 9847, "12": 187184, "13": 195639, "14": 226913, "15": 246258, "21": 266764, "22": 279870, "23": 291099, "24": 299160, "25": 307290, "31": 324144, "32": 329586, "33": 331620, "34": 335008, "35": 331935, "41": 340870, "42": 330854, "43": 320980, "44": 306901, "45": 292398, "51": 292724, "52": 267040, "53": 244539, "54": 223683, "55": 204458, "61": 202726, "62": 174886, "63": 151917, "64": 131582, "65": 115303, "71": 131441, "72": 111648, "73": 91356, "74": 74286, "75": 67750, "80": 341028}},
  {"date": "2026-09-30", "source": "manual", "total": 8615104, "bins": {"11": 9448, "12": 155196, "13": 164981, "14": 196341, "15": 217328, "21": 241156, "22": 257506, "23": 272985, "24": 284464, "25": 294874, "31": 315312, "32": 324745, "33": 330226, "34": 336671, "35": 337237, "41": 353165, "42": 345968, "43": 341488, "44": 332304, "45": 321394, "51": 330411, "52": 306716, "53": 284293, "54": 263353, "55": 240930, "61": 237321, "62": 204445, "63": 175965, "64": 150739, "65": 129981, "71": 144299, "72": 119670, "73": 96575, "74": 79604, "75": 75467, "80": 342546}},
  {"date": "2026-10-01", "source": "manual", "total": 8621789, "bins": {"11": 9445, "12": 154838, "13": 164609, "14": 195873, "15": 217032, "21": 240734, "22": 257171, "23": 272669, "24": 284279, "25": 294852, "31": 315113, "32": 324650, "33": 330255, "34": 336803, "35": 337505, "41": 353422, "42": 346403, "43": 341906, "44": 332958, "45": 322180, "51": 331162, "52": 307753, "53": 285129, "54": 264233, "55": 241783, "61": 237652, "62": 204850, "63": 176299, "64": 150975, "65": 130314, "71": 144524, "72": 119777, "73": 96715, "74": 79698, "75": 75631, "80": 342597}}
]
```

`data/stratz.json` (values transcribed from the Esports Tales Season 6 tables; each medal array is stars 1–5):

```json
{
  "source": "Esports Tales / Stratz",
  "source_url": "https://www.esportstales.com/dota-2/seasonal-rank-distribution-and-mmr-medals",
  "default_population": 7000000,
  "events": [
    { "date": "2026-06-18", "label": "Lower-rank win gains raised (+35 to +40 vs \u221225)" }
  ],
  "months": [
    { "month": "2023-05", "cumulative": {
      "herald": [0.03, 0.32, 0.77, 1.46, 2.53],
      "guardian": [4.12, 6.3, 9.22, 12.95, 17.47],
      "crusader": [22.85, 28.81, 35.07, 41.47, 47.69],
      "archon": [53.74, 59.34, 64.43, 69.01, 73.08],
      "legend": [76.8, 80.05, 82.9, 85.36, 87.49],
      "ancient": [89.41, 91.03, 92.42, 93.6, 94.58],
      "divine": [95.64, 96.53, 97.23, 97.78, 98.22],
      "immortal": [99.99] } },
    { "month": "2023-07", "cumulative": {
      "herald": [0.05, 0.7, 1.55, 2.74, 4.36],
      "guardian": [6.51, 9.23, 12.57, 16.52, 21.07],
      "crusader": [26.26, 31.82, 37.59, 43.42, 49.1],
      "archon": [54.71, 59.96, 64.78, 69.14, 73.04],
      "legend": [76.72, 79.94, 82.75, 85.19, 87.32],
      "ancient": [89.29, 90.95, 92.35, 93.53, 94.52],
      "divine": [95.61, 96.51, 97.22, 97.77, 98.21],
      "immortal": [99.99] } },
    { "month": "2023-09", "cumulative": {
      "herald": [0.06, 1.0, 2.14, 3.68, 5.64],
      "guardian": [8.13, 11.13, 14.66, 18.65, 23.11],
      "crusader": [28.09, 33.37, 38.81, 44.27, 49.6],
      "archon": [54.91, 59.9, 64.53, 68.76, 72.59],
      "legend": [76.24, 79.44, 82.27, 84.73, 86.89],
      "ancient": [88.91, 90.62, 92.05, 93.27, 94.3],
      "divine": [95.43, 96.36, 97.1, 97.67, 98.12],
      "immortal": [99.99] } },
    { "month": "2023-11", "cumulative": {
      "herald": [0.07, 1.38, 2.86, 4.74, 7.03],
      "guardian": [9.82, 13.07, 16.77, 20.86, 25.32],
      "crusader": [30.21, 35.33, 40.55, 45.78, 50.86],
      "archon": [55.94, 60.69, 65.13, 69.2, 72.91],
      "legend": [76.46, 79.58, 82.34, 84.76, 86.88],
      "ancient": [88.88, 90.6, 92.02, 93.22, 94.25],
      "divine": [95.39, 96.34, 97.07, 97.64, 98.09],
      "immortal": [99.99] } },
    { "month": "2024-01", "cumulative": {
      "herald": [0.08, 1.54, 3.2, 5.27, 7.73],
      "guardian": [10.66, 14.01, 17.75, 21.83, 26.21],
      "crusader": [31.01, 35.98, 41.01, 46.05, 50.94],
      "archon": [55.86, 60.48, 64.82, 68.78, 74.23],
      "legend": [75.96, 79.08, 81.84, 84.27, 86.42],
      "ancient": [88.47, 90.21, 91.68, 92.92, 93.67],
      "divine": [93.98, 96.15, 96.91, 97.5, 97.98],
      "immortal": [99.99] } },
    { "month": "2024-10", "cumulative": {
      "herald": [0.12, 2.44, 4.67, 7.23, 10.1],
      "guardian": [13.34, 16.84, 20.59, 24.49, 28.57],
      "crusader": [32.92, 37.32, 41.73, 46.09, 50.35],
      "archon": [54.64, 58.72, 62.55, 66.15, 69.49],
      "legend": [72.86, 75.87, 78.59, 81.04, 83.25],
      "ancient": [85.46, 87.37, 89.0, 90.41, 91.65],
      "divine": [93.12, 94.35, 95.34, 96.11, 96.78],
      "immortal": [99.99] } },
    { "month": "2024-12", "cumulative": {
      "herald": [0.13, 2.65, 5.01, 7.69, 10.64],
      "guardian": [13.95, 17.5, 21.26, 25.16, 29.19],
      "crusader": [33.49, 37.83, 42.16, 46.44, 50.61],
      "archon": [54.81, 58.81, 62.57, 66.09, 69.37],
      "legend": [72.69, 75.67, 78.35, 80.77, 82.96],
      "ancient": [85.17, 87.08, 88.71, 90.13, 91.38],
      "divine": [92.86, 94.11, 95.12, 95.91, 96.6],
      "immortal": [99.99] } },
    { "month": "2025-02", "cumulative": {
      "herald": [0.14, 2.83, 5.33, 8.1, 11.14],
      "guardian": [14.51, 18.1, 21.87, 25.76, 29.77],
      "crusader": [34.02, 38.3, 42.55, 46.76, 50.85],
      "archon": [54.98, 58.91, 62.6, 66.05, 69.28],
      "legend": [72.54, 75.47, 78.13, 80.52, 82.71],
      "ancient": [84.9, 86.8, 88.44, 89.86, 91.12],
      "divine": [92.61, 93.88, 94.9, 95.71, 96.42],
      "immortal": [99.99] } },
    { "month": "2025-04", "cumulative": {
      "herald": [0.15, 2.82, 5.35, 8.17, 11.25],
      "guardian": [14.66, 18.27, 22.05, 25.91, 29.9],
      "crusader": [34.12, 38.34, 42.54, 46.68, 50.71],
      "archon": [54.78, 58.64, 62.3, 65.71, 68.91],
      "legend": [72.13, 75.05, 77.7, 80.09, 82.27],
      "ancient": [84.47, 86.37, 88.03, 89.47, 90.75],
      "divine": [92.28, 93.58, 94.63, 95.47, 96.22],
      "immortal": [99.99] } },
    { "month": "2025-08", "cumulative": {
      "herald": [0.19, 3.11, 5.86, 8.87, 12.11],
      "guardian": [15.62, 19.31, 23.12, 27.01, 30.99],
      "crusader": [35.15, 39.3, 43.42, 47.47, 51.4],
      "archon": [55.36, 59.1, 62.65, 65.97, 69.08],
      "legend": [72.21, 75.04, 77.62, 79.96, 82.11],
      "ancient": [84.26, 86.13, 87.76, 89.19, 90.48],
      "divine": [91.99, 93.29, 94.35, 95.22, 95.99],
      "immortal": [99.99] } },
    { "month": "2025-10", "cumulative": {
      "herald": [0.2, 3.28, 6.17, 9.3, 12.63],
      "guardian": [16.23, 19.97, 23.82, 27.74, 31.71],
      "crusader": [35.85, 39.98, 44.05, 48.06, 51.94],
      "archon": [55.83, 59.51, 63.0, 66.26, 69.34],
      "legend": [72.41, 75.18, 77.71, 80.02, 82.15],
      "ancient": [84.26, 86.1, 87.72, 89.14, 90.42],
      "divine": [91.91, 93.21, 94.26, 95.12, 95.91],
      "immortal": [99.99] } },
    { "month": "2025-12", "cumulative": {
      "herald": [0.21, 3.43, 6.43, 9.67, 13.08],
      "guardian": [16.75, 20.54, 24.42, 28.35, 32.33],
      "crusader": [36.45, 40.56, 44.6, 48.56, 52.4],
      "archon": [56.24, 59.88, 63.32, 66.53, 69.56],
      "legend": [72.58, 75.32, 77.81, 80.09, 82.18],
      "ancient": [84.27, 86.1, 87.7, 89.1, 90.37],
      "divine": [91.85, 93.13, 94.19, 95.05, 95.84],
      "immortal": [99.99] } },
    { "month": "2026-02", "cumulative": {
      "herald": [0.23, 3.57, 6.7, 10.03, 13.54],
      "guardian": [17.27, 21.12, 25.03, 28.98, 32.95],
      "crusader": [37.05, 41.13, 45.15, 49.07, 52.87],
      "archon": [56.66, 60.25, 63.64, 66.81, 69.79],
      "legend": [72.77, 75.46, 77.92, 80.17, 82.23],
      "ancient": [84.3, 86.1, 87.69, 89.07, 90.33],
      "divine": [91.8, 93.07, 94.12, 94.99, 95.78],
      "immortal": [99.99] } },
    { "month": "2026-04", "cumulative": {
      "herald": [0.24, 3.7, 6.93, 10.35, 13.92],
      "guardian": [17.72, 21.6, 25.54, 29.5, 33.46],
      "crusader": [37.56, 41.62, 45.61, 49.51, 53.27],
      "archon": [57.02, 60.57, 63.92, 67.06, 69.99],
      "legend": [72.93, 75.59, 78.02, 80.24, 82.28],
      "ancient": [84.32, 86.11, 87.68, 89.05, 90.3],
      "divine": [91.76, 93.02, 94.07, 94.93, 95.72],
      "immortal": [99.99] } },
    { "month": "2026-06", "cumulative": {
      "herald": [0.25, 3.74, 7.02, 10.51, 14.15],
      "guardian": [18.01, 21.93, 25.9, 29.86, 33.82],
      "crusader": [37.92, 41.97, 45.92, 49.78, 53.51],
      "archon": [57.22, 60.72, 64.04, 67.13, 70.03],
      "legend": [72.93, 75.56, 77.96, 80.16, 82.18],
      "ancient": [84.21, 85.98, 87.54, 88.91, 90.15],
      "divine": [91.6, 92.87, 93.92, 94.78, 95.59],
      "immortal": [99.99] } },
    { "month": "2026-08", "published": "2026-08-04", "cumulative": {
      "herald": [0.23, 3.1, 5.89, 8.94, 12.23],
      "guardian": [15.8, 19.5, 23.29, 27.12, 30.99],
      "crusader": [35.02, 39.04, 43.0, 46.9, 50.7],
      "archon": [54.54, 58.21, 61.72, 65.03, 68.16],
      "legend": [71.31, 74.18, 76.81, 79.22, 81.44],
      "ancient": [83.65, 85.59, 87.28, 88.76, 90.06],
      "divine": [91.55, 92.83, 93.88, 94.75, 95.56],
      "immortal": [99.99] } }
  ]
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 7 tests` … `OK`.

- [ ] **Step 5: Commit**

```powershell
git add .gitignore data/stratz.json data/opendota.json tests/test_data.py
git commit -m "Add Stratz percentile history and data validation tests"
```

---

### Task 2: OpenDota snapshot script

**Files:**
- Create: `scripts/snapshot.py`
- Test: `tests/test_snapshot.py`

**Interfaces:**
- Produces: `snapshot.fetch(url=URL, timeout=30) -> tuple[list[dict], int]`, `snapshot.to_entry(rows, total, date) -> dict`, `snapshot.append(entries, entry) -> list`, `snapshot.main(path=DATA_PATH, fetch_fn=fetch, today=None) -> int`. Entry shape `{"date": "YYYY-MM-DD", "total": int, "bins": {"11": int, ..., "80": int}}`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_snapshot.py`:

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import snapshot  # noqa: E402

SAMPLE_ROWS = [
    {"bin": 11, "bin_name": 11, "count": 9448, "cumulative_sum": 9448},
    {"bin": 12, "bin_name": 12, "count": 155196, "cumulative_sum": 164644},
    {"bin": 80, "bin_name": 80, "count": 342546, "cumulative_sum": 507190},
]
SAMPLE_TOTAL = 507190


class ToEntryTest(unittest.TestCase):
    def test_builds_expected_shape(self):
        entry = snapshot.to_entry(SAMPLE_ROWS, SAMPLE_TOTAL, "2026-10-05")
        self.assertEqual(
            entry,
            {"date": "2026-10-05", "total": 507190, "bins": {"11": 9448, "12": 155196, "80": 342546}},
        )


class AppendTest(unittest.TestCase):
    def test_adds_new_date(self):
        existing = [{"date": "2026-10-05", "total": 1, "bins": {}}]
        new = {"date": "2026-10-12", "total": 2, "bins": {}}
        self.assertEqual(snapshot.append(existing, new), existing + [new])

    def test_duplicate_date_is_noop(self):
        existing = [{"date": "2026-10-05", "total": 1, "bins": {}}]
        dup = {"date": "2026-10-05", "total": 99, "bins": {"11": 1}}
        self.assertEqual(snapshot.append(existing, dup), existing)

    def test_does_not_mutate_input(self):
        existing = []
        snapshot.append(existing, {"date": "2026-10-05", "total": 1, "bins": {}})
        self.assertEqual(existing, [])

    def test_keeps_dates_sorted(self):
        existing = [{"date": "2026-10-12", "total": 1, "bins": {}}]
        older = {"date": "2026-10-05", "total": 2, "bins": {}}
        self.assertEqual([e["date"] for e in snapshot.append(existing, older)], ["2026-10-05", "2026-10-12"])


class MainTest(unittest.TestCase):
    def test_fetch_failure_exits_1_and_leaves_file_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "opendota.json"
            path.write_text("[]", encoding="utf-8")

            def boom():
                raise OSError("no network")

            rc = snapshot.main(path=path, fetch_fn=boom, today="2026-10-05")
            self.assertEqual(rc, 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "[]")

    def test_success_appends_entry(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "opendota.json"
            path.write_text("[]", encoding="utf-8")
            rc = snapshot.main(path=path, fetch_fn=lambda: (SAMPLE_ROWS, SAMPLE_TOTAL), today="2026-10-05")
            self.assertEqual(rc, 0)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["date"], "2026-10-05")
            self.assertEqual(data[0]["bins"]["80"], 342546)

    def test_second_run_same_day_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "opendota.json"
            path.write_text("[]", encoding="utf-8")
            fetch_fn = lambda: (SAMPLE_ROWS, SAMPLE_TOTAL)  # noqa: E731
            snapshot.main(path=path, fetch_fn=fetch_fn, today="2026-10-05")
            snapshot.main(path=path, fetch_fn=fetch_fn, today="2026-10-05")
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_snapshot -v`
Expected: `ModuleNotFoundError: No module named 'snapshot'`.

- [ ] **Step 3: Write the script**

Create `scripts/snapshot.py`:

```python
"""Append today's OpenDota rank distribution to data/opendota.json.

Run by .github/workflows/snapshot.yml weekly. Safe to rerun: one entry per date.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://api.opendota.com/api/distributions"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "opendota.json"
USER_AGENT = "dota-mmr-shift snapshot (https://github.com)"


def fetch(url: str = URL, timeout: int = 30) -> tuple[list[dict], int]:
    """Return (rows, total) from OpenDota's ranks distribution."""
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    ranks = payload["ranks"]
    return ranks["rows"], int(ranks["sum"]["count"])


def to_entry(rows: list[dict], total: int, date: str) -> dict:
    bins = {str(row["bin"]): int(row["count"]) for row in rows}
    return {"date": date, "total": int(total), "bins": bins}


def append(entries: list[dict], entry: dict) -> list[dict]:
    if any(e["date"] == entry["date"] for e in entries):
        return list(entries)
    return sorted([*entries, entry], key=lambda e: e["date"])


def main(path: Path = DATA_PATH, fetch_fn=fetch, today: str | None = None) -> int:
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        rows, total = fetch_fn()
    except Exception as exc:  # network, HTTP, JSON, or schema failure
        print(f"snapshot failed: {exc}", file=sys.stderr)
        return 1
    entries = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    updated = append(entries, to_entry(rows, total, today))
    if updated != entries:
        path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        print(f"added snapshot for {today} ({total} profiles)")
    else:
        print(f"snapshot for {today} already present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 15 tests` … `OK`.

- [ ] **Step 5: Smoke-run against the live API**

Run: `python scripts/snapshot.py; git diff --stat`
Expected: if today is 2026-10-01, prints `snapshot for 2026-10-01 already present` and no diff. On a later date, prints `added snapshot for …` and `data/opendota.json` gains one entry; keep it (it is a real snapshot) and include it in the commit below.

- [ ] **Step 6: Commit**

```powershell
git add scripts/snapshot.py tests/test_snapshot.py data/opendota.json
git commit -m "Add OpenDota snapshot script with tests"
```

---

### Task 3: GitHub Actions cron and README

**Files:**
- Create: `.github/workflows/snapshot.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: `scripts/snapshot.py` (Task 2) writing `data/opendota.json`.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/snapshot.yml`:

```yaml
name: OpenDota snapshot

on:
  schedule:
    - cron: "0 6 * * *"   # daily 06:00 UTC
  workflow_dispatch:

permissions:
  contents: write

jobs:
  snapshot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Fetch distribution
        run: python scripts/snapshot.py
      - name: Commit if changed
        run: |
          if git diff --quiet -- data/opendota.json; then
            echo "No change"
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/opendota.json
          git commit -m "Add OpenDota snapshot $(date -u +%F)"
          git push
```

- [ ] **Step 2: Write the README**

Create `README.md`:

````markdown
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
````

- [ ] **Step 3: Commit**

```powershell
git add .github/workflows/snapshot.yml README.md
git commit -m "Add weekly OpenDota snapshot workflow and README"
```

---

### Task 4: Page skeleton, data loading, derivations, headline cards

**Files:**
- Create: `index.html`

**Interfaces:**
- Produces (JS globals used by later tasks): `MEDALS`, `LABEL`, `FOCUS`, `HEX`, `state` (`{data, population, monthIndex, view, opendota, snapshots}`), `medalShares(cumulative) -> {medal: pct}`, `starShares(cumulative) -> [{medal, star, label, share}]`, `round2`, `count(sharePct, pop)`, `fmt`, `fmtDelta`, `monthLabel("YYYY-MM")`, `monthDate("YYYY-MM") -> Date(UTC)`, `eventFraction(months, isoDate) -> number|null`, `loadJSON(path)`, `renderHeadline()`, `renderAll()`. HTML anchors `<!-- @timeline -->`, `<!-- @trend -->`, `<!-- @opendota -->`, `<!-- @breakeven -->`, `<!-- @method -->`, `<!-- @og -->` and JS anchors `// @timeline-js`, `// @trend-js`, `// @opendota-js`, `// @breakeven-js`, `// @init`, `// @renderAll`. Later tasks replace these anchor lines with their blocks.

- [ ] **Step 1: Write `index.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dota 2 rank distribution since the June 2026 MMR change</title>
<meta name="description" content="How many players are in Crusader, Archon, and Legend before and after Valve raised lower-rank MMR gains in June 2026. Stratz percentiles via Esports Tales, live OpenDota counts.">
<!-- @og -->
<style>
:root{--bg:#0f1115;--panel:#171a21;--line:#2a2f3a;--text:#e6e8ee;--muted:#9aa3b2;--accent:#5aa9ff;--up:#4cc38a;--down:#e5534b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;line-height:1.2;margin:0 0 8px}
h2{font-size:20px;margin:40px 0 8px}
h3{font-size:16px;margin:24px 0 4px}
p{margin:8px 0}
a{color:var(--accent)}
.muted{color:var(--muted)}
.small{font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px}
.card h3{margin:0 0 6px;font-size:15px}
.card .big{font-size:26px;font-weight:600}
.card .delta{font-weight:600}
.up{color:var(--up)}.down{color:var(--down)}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0}
label{color:var(--muted);font-size:14px}
input[type=number]{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:15px;width:150px}
input[type=range]{width:100%;margin:0}
button{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 12px;font-size:14px;cursor:pointer}
button.on{border-color:var(--accent);color:var(--accent)}
.chart-title{font-weight:600;margin:16px 0 4px}
.caption{color:var(--muted);font-size:13px;margin-top:6px}
.axis-label{font-size:12px;color:var(--muted);margin:0 0 4px 36px}
.bars{display:flex;align-items:flex-end;gap:6px;height:260px;margin-left:36px;border-left:1px solid var(--line);border-bottom:1px solid var(--line);padding:0 4px;position:relative}
.bars::before{content:attr(data-ymax);position:absolute;left:-36px;top:-7px;font-size:11px;color:var(--muted)}
.bars::after{content:"0%";position:absolute;left:-24px;bottom:-7px;font-size:11px;color:var(--muted)}
.bar-group{flex:1;display:flex;align-items:flex-end;justify-content:center;height:100%;position:relative}
.bar{width:100%;background:var(--accent);border-radius:2px 2px 0 0;transition:height .5s ease,background .5s ease;position:relative}
.bar .val{position:absolute;top:-18px;left:0;right:0;text-align:center;font-size:11px;color:var(--muted);white-space:nowrap}
.xlabels{display:flex;gap:6px;margin-left:36px;padding:4px 4px 0;font-size:12px;color:var(--muted)}
.xlabels div{flex:1;text-align:center;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;margin:6px 0}
.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;background:currentColor;vertical-align:middle}
.slider-wrap{flex:1;min-width:200px;position:relative;padding-top:10px}
.event-marker{position:absolute;top:0;width:2px;height:10px;background:var(--down);pointer-events:none}
svg.line{width:100%;height:auto;display:block;background:var(--panel);border:1px solid var(--line);border-radius:8px}
.hidden{display:none}
.stat{display:inline-block;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:6px 8px 6px 0}
.stat .big{font-size:22px;font-weight:600}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;margin-top:12px}
table{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}
th,td{padding:8px 10px;text-align:right;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:500;background:var(--panel);position:sticky;top:0}
th:first-child,td:first-child{text-align:left}
tr:last-child td{border-bottom:none}
tr.focus td{background:rgba(90,169,255,.06)}
td .sub{display:block;font-size:12px;color:var(--muted)}
</style>
</head>
<body>
<main>
<h1>Dota 2 rank distribution since the June 2026 MMR change</h1>
<p class="muted">From about 18 June 2026, ranked wins below roughly 4k MMR pay +35 to +40 while losses stay near −25. This page tracks what that did to the medal ladder, and keeps tracking it.</p>
<div id="error" class="hidden" style="color:var(--down)"></div>

<section id="headline">
  <div class="controls">
    <label for="population">Assumed ranked population</label>
    <input id="population" type="number" min="1000" step="100000">
  </div>
  <div class="cards" id="cards"></div>
  <p class="caption" id="headline-note"></p>
  <div class="chart-title" id="medal-table-title"></div>
  <div class="tbl-wrap"><table id="medal-table"></table></div>
  <p class="caption">Share = star-5 cumulative percentile of the medal minus that of the medal below. Count = share × population. "pt" = percentage points. Source: Stratz percentiles via Esports Tales.</p>
</section>

<!-- @timeline -->
<!-- @trend -->
<!-- @opendota -->
<!-- @breakeven -->
<!-- @method -->
</main>

<script>
const MEDALS = ["herald","guardian","crusader","archon","legend","ancient","divine","immortal"];
const LABEL = {herald:"Herald",guardian:"Guardian",crusader:"Crusader",archon:"Archon",legend:"Legend",ancient:"Ancient",divine:"Divine",immortal:"Immortal"};
const FOCUS = ["crusader","archon","legend"];
const HEX = {herald:"#6b7280",guardian:"#6b7280",crusader:"#c9a227",archon:"#5aa9ff",legend:"#c77dff",ancient:"#6b7280",divine:"#6b7280",immortal:"#6b7280"};
const BASELINE_MONTH = "2026-06";

const state = {data:null, population:7000000, monthIndex:0, view:"medal", opendota:null, snapshots:[]};

function round2(x){ return Math.round(x*100)/100; }
function count(sharePct, pop){ return Math.round(sharePct/100*pop); }
function fmt(n){ return n.toLocaleString("en-US"); }
function fmtDelta(n){ return (n>0?"+":"") + fmt(n); }
function monthLabel(ym){ const [y,m]=ym.split("-").map(Number); return new Date(y, m-1, 1).toLocaleString("en-US",{month:"short",year:"numeric"}); }
function monthDate(ym){ const [y,m]=ym.split("-").map(Number); return new Date(Date.UTC(y, m-1, 1)); }

function medalShares(c){
  const out={}; let floor=0;
  for (const m of MEDALS){
    if (m==="immortal"){ out[m]=round2(100-floor); break; }
    const top=c[m][c[m].length-1]; out[m]=round2(top-floor); floor=top;
  }
  return out;
}
function starShares(c){
  const out=[]; let prev=0;
  for (const m of MEDALS){
    if (m==="immortal"){ out.push({medal:m, star:0, label:"Imm", share:round2(100-prev)}); break; }
    c[m].forEach((v,i)=>{ out.push({medal:m, star:i+1, label:LABEL[m].slice(0,3)+" "+(i+1), share:round2(v-prev)}); prev=v; });
  }
  return out;
}
function eventFraction(months, iso){
  const d=new Date(iso+"T00:00:00Z"); const ds=months.map(m=>monthDate(m.month));
  for (let i=0;i<ds.length-1;i++){
    if (d>=ds[i] && d<=ds[i+1]){ const f=(d-ds[i])/(ds[i+1]-ds[i]); return (i+f)/(ds.length-1); }
  }
  return null;
}
async function loadJSON(path){ const r=await fetch(path); if(!r.ok) throw new Error(path+" "+r.status); return r.json(); }

function renderHeadline(){
  const months=state.data.months;
  const base=months.find(m=>m.month===BASELINE_MONTH);
  const latest=months[months.length-1];
  const bs=medalShares(base.cumulative), ls=medalShares(latest.cumulative);
  const el=document.getElementById("cards"); el.innerHTML="";
  for (const m of FOCUS){
    const b=count(bs[m], state.population), l=count(ls[m], state.population), d=l-b;
    const card=document.createElement("div"); card.className="card";
    card.innerHTML=`<h3 style="color:${HEX[m]}">${LABEL[m]}</h3>
      <div class="big">${fmt(l)}</div>
      <div class="muted small">${monthLabel(latest.month)} · ${ls[m].toFixed(2)}% of players</div>
      <div class="delta ${d>=0?"up":"down"}">${fmtDelta(d)} since ${monthLabel(base.month)}</div>
      <div class="muted small">${fmt(b)} · ${bs[m].toFixed(2)}% in ${monthLabel(base.month)}</div>`;
    el.appendChild(card);
  }
  document.getElementById("headline-note").textContent =
    `Counts are ${fmt(state.population)} × medal share. Percentages are the measurement; counts are scaled. Source: Stratz percentiles via Esports Tales, ${monthLabel(base.month)} (last table before the change) and ${monthLabel(latest.month)} (latest).`;
  renderMedalTable(base, latest, bs, ls);
}

function deltaCell(n, suffix=""){ return `<td class="${n>=0?"up":"down"}">${fmtDelta(n)}${suffix}</td>`; }
function renderMedalTable(base, latest, bs, ls){
  const bl=monthLabel(base.month), ll=monthLabel(latest.month);
  document.getElementById("medal-table-title").textContent=`All medals: ${bl} vs ${ll}`;
  let h=`<thead><tr><th>Medal</th><th>${bl} players</th><th>${ll} players</th><th>Change</th><th>${bl} share</th><th>${ll} share</th><th>Change</th></tr></thead><tbody>`;
  for (const m of MEDALS){
    const b=count(bs[m], state.population), l=count(ls[m], state.population);
    h+=`<tr class="${FOCUS.includes(m)?"focus":""}"><td style="color:${HEX[m]}">${LABEL[m]}</td><td>${fmt(b)}</td><td>${fmt(l)}</td>${deltaCell(l-b)}<td>${bs[m].toFixed(2)}%</td><td>${ls[m].toFixed(2)}%</td>${deltaCell(round2(ls[m]-bs[m])," pt")}</tr>`;
  }
  document.getElementById("medal-table").innerHTML=h+"</tbody>";
}

function renderAll(){
  renderHeadline();
  // @renderAll
}

// @timeline-js
// @trend-js
// @opendota-js
// @breakeven-js

async function init(){
  state.data = await loadJSON("data/stratz.json");
  state.population = state.data.default_population;
  state.monthIndex = state.data.months.length-1;
  document.getElementById("population").value = state.population;
  renderHeadline();
  // @init
}
document.getElementById("population").addEventListener("input", e=>{
  const v=Number(e.target.value); if (v>0){ state.population=v; renderAll(); }
});
init().catch(err=>{ const e=document.getElementById("error"); e.textContent="Could not load data: "+err.message; e.classList.remove("hidden"); });
</script>
</body>
</html>
```

- [ ] **Step 2: Serve and check in the browser**

Run (leave running in a background terminal): `python -m http.server 8765`

Open `http://localhost:8765/` in the Cursor browser (`browser_navigate`) and take a `browser_snapshot`. Expected cards:

- Crusader: `1,379,700` · Aug 2026 · 19.71% · `+1,400 since Jun 2026` · `1,378,300 · 19.69% in Jun 2026`
- Archon: `1,222,200` · 17.46% · `+65,800` · `1,156,400 · 16.52%`
- Legend: `929,600` · 13.28% · `+79,100` · `850,500 · 12.15%`

Type `10000000` in the population field; Crusader should show `1,971,000` and `+2,000`.

- [ ] **Step 3: Commit**

```powershell
git add index.html
git commit -m "Add page skeleton with headline bracket counts"
```

---

### Task 5: Timeline slider, play button, animated bar chart, medal/star toggle, URL state

**Files:**
- Modify: `index.html` (replace `<!-- @timeline -->`, `// @timeline-js`, `// @init`, `// @renderAll`)

**Interfaces:**
- Consumes: `state`, `MEDALS`, `LABEL`, `HEX`, `medalShares`, `starShares`, `monthLabel`, `eventFraction`.
- Produces: `drawBars(barsEl, xEl, items, yMax, showValues)` where `items = [{label, share, color}]` (reused by Task 7), `renderBars()`, `setupTimeline()`, `startPlay()`, `stopPlay()`, `setView("medal"|"star")`, `writeURL()`.

- [ ] **Step 1: Replace `<!-- @timeline -->` with the section markup**

```html
<section id="timeline">
  <h2>Medal share over time</h2>
  <p class="muted small">Drag the slider or press Play. The red tick marks 18 June 2026, when the gain change appeared.</p>
  <div class="controls">
    <button id="play">Play</button>
    <div class="slider-wrap">
      <input type="range" id="month-slider" min="0" step="1">
      <div id="event-marker" class="event-marker"></div>
    </div>
    <span id="month-label" style="min-width:90px;font-weight:600"></span>
    <button id="view-medal" class="on">8 medals</button>
    <button id="view-star">36 stars</button>
  </div>
  <div id="event-label" class="small" style="color:var(--down)"></div>
  <div class="chart-title" id="bars-title"></div>
  <div class="axis-label">Share of calibrated accounts (%)</div>
  <div class="bars" id="bars"></div>
  <div class="xlabels" id="bars-x"></div>
  <div class="caption" id="bars-caption"></div>
</section>
<!-- @trend -->
```

(The `<!-- @trend -->` anchor is kept for Task 6.)

- [ ] **Step 2: Replace `// @timeline-js` with the JS**

```js
function drawBars(barsEl, xEl, items, yMax, showValues){
  barsEl.dataset.ymax = yMax + "%";
  if (barsEl.childElementCount !== items.length){
    barsEl.innerHTML=""; xEl.innerHTML="";
    items.forEach(()=>{
      const g=document.createElement("div"); g.className="bar-group";
      const b=document.createElement("div"); b.className="bar"; b.style.height="0%";
      const v=document.createElement("span"); v.className="val"; b.appendChild(v);
      g.appendChild(b); barsEl.appendChild(g);
      xEl.appendChild(document.createElement("div"));
    });
  }
  [...barsEl.children].forEach((g,i)=>{
    const it=items[i], b=g.firstElementChild;
    b.style.height = Math.min(100, it.share/yMax*100) + "%";
    b.style.background = it.color;
    b.title = `${it.label}: ${it.share.toFixed(2)}%`;
    b.firstElementChild.textContent = showValues ? it.share.toFixed(1)+"%" : "";
    xEl.children[i].textContent = it.label;
  });
}

function barItems(){
  const c=state.data.months[state.monthIndex].cumulative;
  if (state.view==="medal"){ const s=medalShares(c); return MEDALS.map(m=>({label:LABEL[m], share:s[m], color:HEX[m]})); }
  return starShares(c).map(s=>({label:s.label, share:s.share, color:HEX[s.medal]}));
}

function renderBars(){
  const months=state.data.months, m=months[state.monthIndex];
  const yMax = state.view==="medal" ? 35 : 8;
  drawBars(document.getElementById("bars"), document.getElementById("bars-x"), barItems(), yMax, state.view==="medal");
  document.getElementById("month-label").textContent = monthLabel(m.month);
  document.getElementById("bars-title").textContent =
    `Share of ranked players by ${state.view==="medal" ? "medal" : "medal and star"} — ${monthLabel(m.month)}`;
  document.getElementById("bars-caption").textContent =
    `Source: Stratz percentiles via Esports Tales · ${monthLabel(months[0].month)} to ${monthLabel(months[months.length-1].month)} · y-axis 0 to ${yMax}%`;
}

let playTimer=null;
function startPlay(){
  const s=document.getElementById("month-slider");
  if (state.monthIndex >= state.data.months.length-1) state.monthIndex=0;
  s.value=state.monthIndex; renderBars();
  document.getElementById("play").textContent="Pause";
  playTimer=setInterval(()=>{
    if (state.monthIndex >= state.data.months.length-1){ stopPlay(); writeURL(); return; }
    state.monthIndex++; s.value=state.monthIndex; renderBars();
  }, 700);
}
function stopPlay(){ if (playTimer){ clearInterval(playTimer); playTimer=null; } document.getElementById("play").textContent="Play"; }
function setView(v){
  state.view=v;
  document.getElementById("view-medal").classList.toggle("on", v==="medal");
  document.getElementById("view-star").classList.toggle("on", v==="star");
  document.getElementById("bars").innerHTML="";
  renderBars();
}
function writeURL(){
  const u=new URL(location.href); u.searchParams.set("month", state.data.months[state.monthIndex].month);
  history.replaceState(null, "", u);
}
function setupTimeline(){
  const months=state.data.months, s=document.getElementById("month-slider");
  s.max=months.length-1;
  const q=new URLSearchParams(location.search).get("month");
  const qi=months.findIndex(m=>m.month===q); if (qi>=0) state.monthIndex=qi;
  s.value=state.monthIndex;
  s.addEventListener("input", ()=>{ stopPlay(); state.monthIndex=Number(s.value); renderBars(); writeURL(); });
  document.getElementById("play").addEventListener("click", ()=> playTimer ? stopPlay() : startPlay());
  document.getElementById("view-medal").addEventListener("click", ()=>setView("medal"));
  document.getElementById("view-star").addEventListener("click", ()=>setView("star"));
  const ev=state.data.events[0], f=eventFraction(months, ev.date);
  if (f!==null){
    document.getElementById("event-marker").style.left=(f*100)+"%";
    document.getElementById("event-label").textContent=`${ev.date}: ${ev.label}`;
  }
  renderBars();
}
// @trend-js
```

(The `// @trend-js` anchor is kept for Task 6.)

- [ ] **Step 3: Wire into init**

Replace `  // @init` with:

```js
  setupTimeline();
  // @init
```

`renderAll` does not need `renderBars` (bars show percentages, not counts); leave `// @renderAll` in place.

- [ ] **Step 4: Check in the browser**

Reload `http://localhost:8765/?month=2026-06`. Expected: slider on Jun 2026, month label "Jun 2026", Crusader bar tallest of the focus three (19.69%). Drag to the far right: URL becomes `?month=2026-08`. Click "36 stars": 36 narrow bars, labels like "Cru 5". Click Play from the end: it restarts at May 2023 and stops at Aug 2026 with the button reading "Play". Red tick sits between the last two slider stops.

- [ ] **Step 5: Commit**

```powershell
git add index.html
git commit -m "Add month timeline with animated medal share bars"
```

---

### Task 6: Trend line chart for Crusader, Archon, Legend

**Files:**
- Modify: `index.html` (replace `<!-- @trend -->`, `// @trend-js`, `// @init`, `// @renderAll`)

**Interfaces:**
- Consumes: `state`, `FOCUS`, `LABEL`, `HEX`, `medalShares`, `monthLabel`, `eventFraction`, `count`, `fmt`.
- Produces: `lineChart(svgEl, {categories, series:[{name, color, values}], yMin, yMax, yLabel, markerX, markerLabel, pointTitle(ser, i, v), xFractions?})` where `xFractions` is an optional array of 0–1 positions per category (defaults to evenly spaced; Task 7 passes date-proportional values); `renderTrend()`.

- [ ] **Step 1: Replace `<!-- @trend -->` with the markup**

```html
<section id="trend-section">
  <h2>Crusader, Archon, and Legend since Season 6 began</h2>
  <div class="chart-title">Share of ranked players by medal, May 2023 to latest</div>
  <div class="legend" id="trend-legend"></div>
  <svg class="line" id="trend" role="img" aria-label="Line chart of Crusader, Archon, and Legend share by month"></svg>
  <div class="caption">Source: Stratz percentiles via Esports Tales · March–July 2024 omitted (OpenDota-sourced) · hover a point for share and scaled count · y-axis: share of calibrated accounts (%)</div>
</section>
<!-- @opendota -->
```

- [ ] **Step 2: Replace `// @trend-js` with the JS**

```js
function lineChart(svg, {categories, series, yMin, yMax, yLabel, markerX=null, markerLabel="", pointTitle, xFractions=null}){
  const W=800, H=320, L=52, R=16, T=20, B=52;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const frac=i=> xFractions ? xFractions[i] : (categories.length===1 ? 0.5 : i/(categories.length-1));
  const x=i=> L + (W-L-R) * frac(i);
  const y=v=> T + (H-T-B) * (1 - (v-yMin)/(yMax-yMin));
  const esc=s=>String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;");
  let s="";
  const ticks=5;
  for (let k=0;k<=ticks;k++){
    const v=yMin+(yMax-yMin)*k/ticks;
    s+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#2a2f3a"/>`;
    s+=`<text x="${L-6}" y="${y(v)+4}" text-anchor="end" font-size="11" fill="#9aa3b2">${v.toFixed(1)}%</text>`;
  }
  let lastLabelX=-Infinity;
  categories.forEach((c,i)=>{
    const last=i===categories.length-1, xi=x(i);
    if (last || xi-lastLabelX>=80){
      if (last && xi-lastLabelX<80) return;
      s+=`<text x="${xi}" y="${H-B+18}" text-anchor="middle" font-size="11" fill="#9aa3b2">${esc(c)}</text>`;
      lastLabelX=xi;
    }
  });
  s+=`<text x="${L}" y="${H-6}" font-size="11" fill="#9aa3b2">${esc(yLabel)}</text>`;
  if (markerX!==null){
    const mx=L+(W-L-R)*markerX;
    s+=`<line x1="${mx}" x2="${mx}" y1="${T}" y2="${H-B}" stroke="#e5534b" stroke-dasharray="4 3"/>`;
    s+=`<text x="${mx+4}" y="${T+12}" font-size="11" fill="#e5534b">${esc(markerLabel)}</text>`;
  }
  for (const ser of series){
    const pts=ser.values.map((v,i)=>`${x(i)},${y(v)}`).join(" ");
    s+=`<polyline points="${pts}" fill="none" stroke="${ser.color}" stroke-width="2"/>`;
    ser.values.forEach((v,i)=>{
      s+=`<circle cx="${x(i)}" cy="${y(v)}" r="3.5" fill="${ser.color}"><title>${esc(pointTitle(ser,i,v))}</title></circle>`;
    });
  }
  svg.innerHTML=s;
}

function renderTrend(){
  const months=state.data.months;
  const cats=months.map(m=>monthLabel(m.month));
  const shares=months.map(m=>medalShares(m.cumulative));
  const series=FOCUS.map(m=>({name:LABEL[m], key:m, color:HEX[m], values:shares.map(s=>s[m])}));
  const ev=state.data.events[0];
  lineChart(document.getElementById("trend"), {
    categories:cats, series, yMin:10, yMax:32,
    yLabel:"Share of calibrated accounts (%)",
    markerX:eventFraction(months, ev.date), markerLabel:"18 Jun 2026 gain change",
    pointTitle:(ser,i,v)=>`${ser.name} · ${cats[i]} · ${v.toFixed(2)}% · ${fmt(count(v, state.population))} players`
  });
  document.getElementById("trend-legend").innerHTML =
    series.map(s=>`<span style="color:${s.color}">${s.name}</span>`).join("");
}
// @opendota-js
```

- [ ] **Step 3: Wire into init and renderAll**

Replace `  // @init` with:

```js
  renderTrend();
  // @init
```

Replace `  // @renderAll` with (no anchor kept; no later task touches `renderAll`):

```js
  renderTrend();
```

- [ ] **Step 4: Check in the browser**

Reload. Expected: three lines; Crusader starts near 30% in May 2023 and ends near 19.7%; Archon and Legend dip to their lowest at Jun 2026 and turn up at Aug 2026; a red dashed marker just before the last point. Hovering the last Legend point shows `Legend · Aug 2026 · 13.28% · 929,600 players`.

- [ ] **Step 5: Commit**

```powershell
git add index.html
git commit -m "Add Crusader, Archon, Legend trend chart"
```

---

### Task 7: OpenDota change-by-bracket table, sparklines, today bar, snapshot trend

**Files:**
- Modify: `index.html` (replace `<!-- @opendota -->`, `// @opendota-js`, `// @init`)

**Interfaces:**
- Consumes: `drawBars` (Task 5), `lineChart` with `xFractions` (Task 6), `deltaCell` (Task 4), `state`, `MEDALS`, `LABEL`, `HEX`, `FOCUS`, `round2`, `fmt`, `fmtDelta`, `loadJSON`.
- Produces: `opendotaMedalCounts(bins) -> {medal: count}`, `opendotaStarCounts(bins) -> [{key, medal, label, count}]`, `opendotaMedalShares(bins, total) -> {medal: pct}`, `snapshotAtOrBefore(snaps, isoDate) -> entry|null`, `isoDaysAgo(n) -> "YYYY-MM-DD"`, `renderChangeTable()`, `renderSparklines()`, `renderTodayBar()`, `renderSnapshotTrend()`, `renderOpenDota()`. State additions: `state.opendota = {bins, total, date, live:boolean}`, `state.snapshots = [...]`, `state.changeView = "medal"|"star"`.

- [ ] **Step 1: Replace `<!-- @opendota -->` with the markup (all blocks start hidden)**

```html
<section id="change-section" class="hidden">
  <h2>Change by bracket, live (OpenDota public profiles)</h2>
  <p class="muted small">"Now" is OpenDota's current distribution, fetched when you opened this page. Each change column compares it with the latest saved snapshot at or before that date. Columns with no snapshot that far back are not shown. 2 Aug 2026 is the earliest saved point after the gain change; 25 Jan 2025 is a pre-change reference.</p>
  <div class="controls">
    <button id="change-medal" class="on">8 medals</button>
    <button id="change-star">36 stars</button>
    <span id="change-now" class="muted small"></span>
  </div>
  <div class="tbl-wrap"><table id="change-table"></table></div>
  <p class="caption" id="change-caption"></p>
  <div id="sparklines" class="hidden">
    <div class="chart-title">Share of public profiles by medal, every saved snapshot</div>
    <div class="cards" id="spark-cards"></div>
    <p class="caption" id="spark-caption"></p>
  </div>
</section>
<section id="opendota-today" class="hidden">
  <h2>OpenDota, public profiles, today</h2>
  <p class="muted small">A different population from the Stratz tables above: only profiles OpenDota has seen with public match data, inactive accounts included. Shown for a live check, not merged into the Stratz series.</p>
  <div class="chart-title" id="today-title"></div>
  <div class="axis-label">Share of public profiles (%)</div>
  <div class="bars" id="today-bars"></div>
  <div class="xlabels" id="today-x"></div>
  <div class="caption" id="today-caption"></div>
</section>
<section id="opendota-trend" class="hidden">
  <h2>OpenDota snapshots over time</h2>
  <div class="chart-title">Crusader, Archon, Legend share of public profiles by snapshot date (x axis proportional to date)</div>
  <div class="legend" id="snap-legend"></div>
  <svg class="line" id="snap" role="img" aria-label="Line chart of OpenDota medal share by snapshot date"></svg>
  <div class="caption" id="snap-caption"></div>
</section>
<!-- @breakeven -->
```

- [ ] **Step 2: Replace `// @opendota-js` with the JS**

```js
state.changeView="medal";
const PERIODS=[
  {key:"d1",  label:"1 day",            daysAgo:1,  tolerance:1},
  {key:"d7",  label:"7 days",           daysAgo:7,  tolerance:3},
  {key:"d30", label:"30 days",          daysAgo:30, tolerance:7},
  {key:"aug", label:"Since 2 Aug 2026", date:"2026-08-02"},
  {key:"jan", label:"Since 25 Jan 2025",date:"2025-01-25"},
];
function isoDaysAgo(n, from){ const d=new Date(Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate())); d.setUTCDate(d.getUTCDate()-n); return d.toISOString().slice(0,10); }
function daysBetween(a, b){ return Math.round((new Date(b+"T00:00:00Z")-new Date(a+"T00:00:00Z"))/864e5); }
function snapshotAtOrBefore(snaps, iso){ let best=null; for (const e of snaps){ if (e.date<=iso) best=e; else break; } return best; }
function periodBaseline(p, snaps, nowIso){
  const target = p.date ? p.date : isoDaysAgo(p.daysAgo, new Date(nowIso+"T00:00:00Z"));
  const e = snapshotAtOrBefore(snaps.filter(s=>s.date<nowIso), target);
  if (!e) return null;
  if (p.daysAgo && daysBetween(e.date, target) > p.tolerance) return null;
  return e;
}
function opendotaMedalCounts(bins){
  const out={}; for (const m of MEDALS) out[m]=0;
  for (const [k,v] of Object.entries(bins)){ const m=MEDALS[Math.floor(Number(k)/10)-1]; if (m) out[m]+=v; }
  return out;
}
function opendotaStarCounts(bins){
  const out=[];
  MEDALS.forEach((m,idx)=>{
    if (m==="immortal"){ out.push({key:"80", medal:m, label:"Immortal", count:bins["80"]||0}); return; }
    for (let s=1;s<=5;s++){ const k=`${idx+1}${s}`; out.push({key:k, medal:m, label:`${LABEL[m]} ${s}`, count:bins[k]||0}); }
  });
  return out;
}
function opendotaMedalShares(bins, total){
  const c=opendotaMedalCounts(bins); const out={}; for (const m of MEDALS) out[m]=round2(c[m]/total*100); return out;
}
function rowsFor(view, bins, total){
  if (view==="medal"){ const c=opendotaMedalCounts(bins); return MEDALS.map(m=>({key:m, medal:m, label:LABEL[m], count:c[m], share:c[m]/total*100})); }
  return opendotaStarCounts(bins).map(r=>({...r, share:r.count/total*100}));
}
function renderChangeTable(){
  const now=state.opendota, snaps=state.snapshots;
  const periods=PERIODS.map(p=>({...p, base:periodBaseline(p, snaps, now.date)})).filter(p=>p.base);
  const nowRows=rowsFor(state.changeView, now.bins, now.total);
  const baseRows=periods.map(p=>Object.fromEntries(rowsFor(state.changeView, p.base.bins, p.base.total).map(x=>[x.key,x])));
  let h=`<thead><tr><th>Bracket</th><th>Now<span class="sub">${now.date}</span></th>`;
  for (const p of periods) h+=`<th>${p.label}<span class="sub">vs ${p.base.date}</span></th>`;
  h+=`</tr></thead><tbody>`;
  for (const r of nowRows){
    h+=`<tr class="${FOCUS.includes(r.medal)?"focus":""}"><td style="color:${HEX[r.medal]}">${r.label}</td><td>${fmt(r.count)}<span class="sub">${r.share.toFixed(2)}%</span></td>`;
    periods.forEach((p,i)=>{
      const b=baseRows[i][r.key], dc=r.count-b.count, ds=round2(r.share-b.share);
      h+=`<td class="${dc>=0?"up":"down"}">${fmtDelta(dc)}<span class="sub">${fmtDelta(ds)} pt</span></td>`;
    });
    h+=`</tr>`;
  }
  document.getElementById("change-table").innerHTML=h+"</tbody>";
  document.getElementById("change-now").textContent=`${fmt(now.total)} public profiles · ${now.live ? "live from OpenDota" : "latest saved snapshot (live fetch failed)"}`;
  document.getElementById("change-caption").textContent=
    `Source: api.opendota.com/api/distributions (now) and ${snaps.length} saved snapshots in this repo, ${snaps[0].date} to ${snaps[snaps.length-1].date}. Changes are in profiles and in percentage points of all public profiles. 7- and 30-day columns appear once a snapshot within ${PERIODS[1].tolerance} and ${PERIODS[2].tolerance} days of the target date exists.`;
  document.getElementById("change-section").classList.remove("hidden");
}
function setChangeView(v){
  state.changeView=v;
  document.getElementById("change-medal").classList.toggle("on", v==="medal");
  document.getElementById("change-star").classList.toggle("on", v==="star");
  renderChangeTable();
}
function dateFractions(dates){
  const t=dates.map(d=>new Date(d+"T00:00:00Z").getTime()), a=t[0], b=t[t.length-1];
  return t.map(v=> b===a ? 0.5 : (v-a)/(b-a));
}
function sparkline(values, fr, color){
  const W=200, H=48, P=4, mn=Math.min(...values), mx=Math.max(...values);
  const y=v=> P+(H-2*P)*(1-(mx===mn ? 0.5 : (v-mn)/(mx-mn)));
  const pts=values.map((v,i)=>`${P+(W-2*P)*fr[i]},${y(v)}`).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:48px;display:block" role="img"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2"/></svg>`;
}
function renderSparklines(){
  const snaps=state.snapshots; if (snaps.length<7) return;
  const fr=dateFractions(snaps.map(s=>s.date));
  const shares=snaps.map(s=>opendotaMedalShares(s.bins, s.total));
  document.getElementById("spark-cards").innerHTML=MEDALS.map(m=>{
    const vals=shares.map(s=>s[m]), first=vals[0], last=vals[vals.length-1];
    return `<div class="card"><h3 style="color:${HEX[m]}">${LABEL[m]}</h3>${sparkline(vals, fr, HEX[m])}<div class="small muted">${first.toFixed(2)}% → ${last.toFixed(2)}% <span class="${last>=first?"up":"down"}">(${fmtDelta(round2(last-first))} pt)</span></div></div>`;
  }).join("");
  document.getElementById("spark-caption").textContent=
    `Source: saved OpenDota snapshots, ${snaps[0].date} to ${snaps[snaps.length-1].date} (${snaps.length} points). x proportional to date; y auto-scaled per medal from first to last value shown below each line.`;
  document.getElementById("sparklines").classList.remove("hidden");
}
function renderTodayBar(){
  const {bins,total}=state.opendota, s=opendotaMedalShares(bins,total);
  const items=MEDALS.map(m=>({label:LABEL[m], share:s[m], color:HEX[m]}));
  drawBars(document.getElementById("today-bars"), document.getElementById("today-x"), items, 35, true);
  const today=new Date().toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"});
  document.getElementById("today-title").textContent=`Share of public profiles by medal — ${today}`;
  document.getElementById("today-caption").textContent=
    `Source: api.opendota.com/api/distributions, fetched on page load · ${fmt(total)} public profiles · Crusader ${fmt(Math.round(s.crusader/100*total))}, Archon ${fmt(Math.round(s.archon/100*total))}, Legend ${fmt(Math.round(s.legend/100*total))}`;
  document.getElementById("opendota-today").classList.remove("hidden");
}
function renderSnapshotTrend(){
  const snaps=state.snapshots, cats=snaps.map(e=>e.date);
  const shares=snaps.map(e=>opendotaMedalShares(e.bins, e.total));
  const series=FOCUS.map(m=>({name:LABEL[m], key:m, color:HEX[m], values:shares.map(s=>s[m])}));
  const all=series.flatMap(s=>s.values);
  const yMin=Math.max(0, Math.floor(Math.min(...all))-1), yMax=Math.ceil(Math.max(...all))+1;
  lineChart(document.getElementById("snap"), {
    categories:cats, series, yMin, yMax, yLabel:"Share of public profiles (%)", xFractions:dateFractions(cats),
    pointTitle:(ser,i,v)=>`${ser.name} · ${cats[i]} · ${v.toFixed(2)}% · ${fmt(Math.round(v/100*snaps[i].total))} profiles`
  });
  document.getElementById("snap-legend").innerHTML=series.map(s=>`<span style="color:${s.color}">${s.name}</span>`).join("");
  document.getElementById("snap-caption").textContent=
    `Source: saved snapshots of api.opendota.com/api/distributions in this repo · ${cats[0]} to ${cats[cats.length-1]} · ${snaps.length} snapshots · no data exists for June–July 2026`;
  document.getElementById("opendota-trend").classList.remove("hidden");
}
async function renderOpenDota(){
  try { const snaps=await loadJSON("data/opendota.json"); if (Array.isArray(snaps)) state.snapshots=snaps; }
  catch (e) { console.warn("OpenDota snapshots skipped:", e.message); }
  let live=null;
  try {
    const r=await fetch("https://api.opendota.com/api/distributions");
    if (!r.ok) throw new Error("HTTP "+r.status);
    const j=await r.json();
    const bins={}; for (const row of j.ranks.rows) bins[String(row.bin)]=row.count;
    live={bins, total:j.ranks.sum.count, date:new Date().toISOString().slice(0,10), live:true};
  } catch (e) { console.warn("OpenDota live fetch skipped:", e.message); }
  const snaps=state.snapshots;
  if (live) state.opendota=live;
  else if (snaps.length){ const l=snaps[snaps.length-1]; state.opendota={bins:l.bins, total:l.total, date:l.date, live:false}; }
  if (state.opendota && snaps.length){
    document.getElementById("change-medal").addEventListener("click", ()=>setChangeView("medal"));
    document.getElementById("change-star").addEventListener("click", ()=>setChangeView("star"));
    renderChangeTable(); renderSparklines();
  }
  if (live) renderTodayBar();
  if (snaps.length>=2) renderSnapshotTrend();
}
// @breakeven-js
```

- [ ] **Step 3: Wire into init**

Replace `  // @init` with:

```js
  renderOpenDota();
  // @init
```

- [ ] **Step 4: Check in the browser**

Reload. Expected:

- "Change by bracket, live" appears. Columns: Bracket, Now (today's date), then only the periods with a qualifying snapshot. On 2026-10-01 with the six seeds: "1 day vs 2026-09-30", "Since 2 Aug 2026 vs 2026-08-02", "Since 25 Jan 2025 vs 2025-01-25"; no 7-day or 30-day column (nearest snapshot is 53 days before the target, beyond tolerance).
- Legend row, "Since 2 Aug 2026" column: count delta is live-minus-1,232,444; with the 2026-10-01 live values (1,425,703 + a day's drift) it reads about `+193,000` to `+200,000`, green. Herald row same column about `−122,000`, red. Share deltas: Legend about `+1.8 pt`, Herald about `−1.7 pt`.
- "36 stars" toggle shows 36 rows with labels like "Legend 1"; "8 medals" returns to 8.
- Sparklines block absent (6 snapshots < 7).
- "OpenDota, public profiles, today" shows 8 bars, caption total above 8,600,000.
- "OpenDota snapshots over time" shows three lines with six points each, the four 2024–2025 points bunched left and the 2026 points right (x is date-proportional); hover on the last Legend point shows `Legend · 2026-10-01 · 16.5…% · 1,43…,… profiles`.

Confirm CORS from the page origin via `browser_cdp Runtime.evaluate` with `fetch("https://api.opendota.com/api/distributions").then(r=>r.ok)` → `true`.

Test the no-live fallback: `browser_cdp Runtime.evaluate` with `window.fetch = (u, ...a) => String(u).includes("opendota.com") ? Promise.reject(new Error("blocked")) : fetch.__orig(u, ...a)` is awkward across reloads; instead temporarily change the fetch URL in `index.html` to `https://api.opendota.com/api/distributions-nope`, reload, and confirm: the change table still renders with "Now 2026-10-01" (from the latest seed) and the note "latest saved snapshot (live fetch failed)"; the today bar is absent; the trend still shows. Revert the URL.

Test the sparkline threshold: temporarily duplicate the last seed entry three times with dates 2026-10-02, 2026-10-03, 2026-10-04 in `data/opendota.json`, reload, confirm 8 sparkline cards appear and the change table gains no 7-day column yet (target 2026-09-24 still resolves to 2026-08-02). Then `git checkout -- data/opendota.json`.

- [ ] **Step 5: Commit**

```powershell
git add index.html
git commit -m "Add live OpenDota bar and snapshot trend"
```

---

### Task 8: Break-even calculator, method and sources, share button, OG tags, OG image

**Files:**
- Modify: `index.html` (replace `<!-- @breakeven -->`, `<!-- @method -->`, `// @breakeven-js`, `// @init`, `<!-- @og -->`)
- Create: `scripts/og_image.py`
- Create: `og-image.png` (generated)

**Interfaces:**
- Consumes: `state`, `medalShares`, `count`, `fmt`.
- Produces: `breakEven(gain, loss) -> pct`, `drift(gain, loss, winRate, games) -> int`, `setupBreakEven()`.

- [ ] **Step 1: Replace `<!-- @breakeven -->` with the markup**

```html
<section id="breakeven">
  <h2>What win rate holds MMR now</h2>
  <div class="controls">
    <label for="gain">MMR per win <b id="gain-v"></b></label>
    <input type="range" id="gain" min="20" max="45" step="1" value="35" style="width:180px">
    <label for="loss">MMR per loss <b id="loss-v"></b></label>
    <input type="range" id="loss" min="20" max="30" step="1" value="25" style="width:180px">
  </div>
  <div>
    <div class="stat"><div class="big" id="be"></div><div class="muted small">win rate that holds MMR</div></div>
    <div class="stat"><div class="big" id="d45"></div><div class="muted small">MMR per 100 games at 45%</div></div>
    <div class="stat"><div class="big" id="d50"></div><div class="muted small">MMR per 100 games at 50%</div></div>
  </div>
  <p class="caption">Break-even = loss ÷ (gain + loss). At the old +25/−25 it was 50%. Reports since June 2026 put wins at +35 to +40 below about 4k MMR, tapering toward +29 around Ancient.</p>
</section>
<!-- @method -->
```

- [ ] **Step 2: Replace `<!-- @method -->` with the markup**

```html
<section id="method">
  <h2>Method and sources</h2>
  <h3>Where the numbers come from</h3>
  <p class="small">Stratz collects the seasonal rank of every calibrated account it can see. <a href="https://www.esportstales.com/dota-2/seasonal-rank-distribution-and-mmr-medals">Esports Tales</a> publishes that as a cumulative percentile per medal and star about every two months, on a sample it describes as over 7 million players in Season 6. Those tables are transcribed into <code>data/stratz.json</code>. March–July 2024 are left out because those months were OpenDota-based.</p>
  <h3>How a medal's share and count are computed</h3>
  <p class="small">Share of a medal = cumulative percentile at its star 5 minus the cumulative percentile at star 5 of the medal below. Herald starts at 0; Immortal is 100 minus Divine 5. Player counts are share × the population in the field at the top, default 7,000,000. Valve publishes no census, so the percentages are the measurement and the counts are scaled from them. Change the population and every count scales with it; the direction of every change does not.</p>
  <h3>Why OpenDota is kept separate</h3>
  <p class="small"><a href="https://api.opendota.com/api/distributions">OpenDota's distribution endpoint</a> counts public profiles it has ever seen, which excludes hidden profiles and keeps inactive ones. It is live and needs no key, so this page fetches it on load and a daily job saves snapshots. It is a different population from Stratz, so it never joins the Stratz series.</p>
  <h3>What resolution the data has</h3>
  <p class="small">Stratz tables arrive about every two months; nothing finer exists. OpenDota recomputes daily, and this repo has saved it daily since 1 October 2026. Before that there are only <a href="https://web.archive.org/web/2026*/https://api.opendota.com/api/distributions">Wayback Machine captures</a> from 5 and 22 August 2024, 25 January 2025, and 2 August 2026. No source has data for June or July 2026, so daily and weekly change can only be shown going forward. The 7-day and 30-day columns switch on once a saved snapshot exists within 3 and 7 days of the target date.</p>
  <h3>The change being measured</h3>
  <p class="small">From around 18–19 June 2026, players below roughly 4k MMR began receiving +35 to +40 per win with losses near −25, even at high rank confidence. Valve did not announce it. First reports: <a href="https://www.reddit.com/r/DotA2/comments/1ud01rb/mmr_gainloss_changes/">MMR gain/loss changes</a>, <a href="https://www.reddit.com/r/DotA2/comments/1umk2in/can_we_get_some_confirmation_on_what_is_going_on/">Can we get some confirmation…</a>, <a href="https://www.reddit.com/r/DotA2/comments/1v67mtd/from_cruzader_to_ancient_in_weeks_new_mmr_cheated/">From Crusader to Ancient in weeks</a>, <a href="https://www.reddit.com/r/DotA2/comments/1w3b34e/any_speculations_on_what_valve_want_to_do_with/">Any speculations on the +40/−25 change?</a>.</p>
  <p class="small"><button id="copy-link">Copy link to this view</button> <span id="copied" class="muted small"></span></p>
  <p class="caption">Source code and data: <a id="repo-link" href="https://github.com">this repository</a>.</p>
</section>
```

- [ ] **Step 3: Replace `// @breakeven-js` with the JS**

```js
function breakEven(gain, loss){ return loss/(gain+loss)*100; }
function drift(gain, loss, winRate, games){ return Math.round(games*(winRate*gain-(1-winRate)*loss)); }
function renderBreakEven(){
  const g=Number(document.getElementById("gain").value), l=Number(document.getElementById("loss").value);
  document.getElementById("gain-v").textContent="+"+g;
  document.getElementById("loss-v").textContent="−"+l;
  document.getElementById("be").textContent=breakEven(g,l).toFixed(1)+"%";
  const d45=drift(g,l,0.45,100), d50=drift(g,l,0.50,100);
  const set=(id,v)=>{ const e=document.getElementById(id); e.textContent=(v>0?"+":"")+v; e.className="big "+(v>=0?"up":"down"); };
  set("d45", d45); set("d50", d50);
}
function setupBreakEven(){
  document.getElementById("gain").addEventListener("input", renderBreakEven);
  document.getElementById("loss").addEventListener("input", renderBreakEven);
  document.getElementById("copy-link").addEventListener("click", async ()=>{
    try { await navigator.clipboard.writeText(location.href); document.getElementById("copied").textContent="Copied."; }
    catch (e) { document.getElementById("copied").textContent=location.href; }
  });
  renderBreakEven();
}
```

- [ ] **Step 4: Wire into init**

Replace `  // @init` with:

```js
  setupBreakEven();
```

- [ ] **Step 5: Find the Pages URL and write the OG tags**

Run: `gh api user -q .login`
Expected: your GitHub login, e.g. `tejas`. The Pages URL will be `https://<login>.github.io/dota-mmr-shift/`.

Replace `<!-- @og -->` with (substitute `<login>`):

```html
<meta property="og:type" content="website">
<meta property="og:title" content="Dota 2 rank distribution since the June 2026 MMR change">
<meta property="og:description" content="Crusader, Archon, and Legend headcounts before and after wins started paying +35 to +40 at lower ranks. Stratz percentiles, live OpenDota counts, updated as new tables publish.">
<meta property="og:url" content="https://<login>.github.io/dota-mmr-shift/">
<meta property="og:image" content="https://<login>.github.io/dota-mmr-shift/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
```

Also set the repo link in the method section: `href="https://github.com/<login>/dota-mmr-shift"` on `#repo-link`.

- [ ] **Step 6: Write the OG image generator**

Create `scripts/og_image.py` (dev-only; needs Pillow):

```python
"""Render og-image.png (1200x630) from data/stratz.json. Dev-only; needs Pillow.

    pip install pillow
    python scripts/og_image.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MEDALS = ["herald", "guardian", "crusader", "archon", "legend", "ancient", "divine", "immortal"]
FOCUS = {"crusader": "#c9a227", "archon": "#5aa9ff", "legend": "#c77dff"}
POP = 7_000_000


def medal_shares(cum: dict) -> dict:
    out, floor = {}, 0.0
    for m in MEDALS:
        if m == "immortal":
            out[m] = 100 - floor
            break
        top = cum[m][-1]
        out[m] = top - floor
        floor = top
    return out


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for name in (["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]):
        p = Path("C:/Windows/Fonts") / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def main() -> None:
    data = json.loads((ROOT / "data" / "stratz.json").read_text(encoding="utf-8"))
    months = data["months"]
    base = next(m for m in months if m["month"] == "2026-06")
    latest = months[-1]
    bs, ls = medal_shares(base["cumulative"]), medal_shares(latest["cumulative"])

    img = Image.new("RGB", (1200, 630), "#0f1115")
    d = ImageDraw.Draw(img)
    d.text((60, 50), "Dota 2 ranks after the June 2026 MMR change", fill="#e6e8ee", font=font(44, True))
    d.text((60, 110), "Players per bracket, Jun 2026 vs latest, on 7,000,000 ranked accounts", fill="#9aa3b2", font=font(24))

    x = 60
    for m, color in FOCUS.items():
        b, l = round(bs[m] / 100 * POP), round(ls[m] / 100 * POP)
        delta = l - b
        d.rounded_rectangle((x, 190, x + 340, 540), radius=16, fill="#171a21", outline="#2a2f3a")
        d.text((x + 24, 214), m.capitalize(), fill=color, font=font(30, True))
        d.text((x + 24, 270), f"{l:,}", fill="#e6e8ee", font=font(48, True))
        d.text((x + 24, 335), f"{ls[m]:.2f}% of players", fill="#9aa3b2", font=font(22))
        d.text((x + 24, 400), f"{'+' if delta >= 0 else ''}{delta:,}", fill="#4cc38a" if delta >= 0 else "#e5534b", font=font(40, True))
        d.text((x + 24, 455), f"since Jun 2026 ({b:,})", fill="#9aa3b2", font=font(22))
        x += 370

    d.text((60, 580), "Source: Stratz percentiles via Esports Tales", fill="#9aa3b2", font=font(20))
    out = ROOT / "og-image.png"
    img.save(out, optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
```

Run:

```powershell
python -m pip install --quiet pillow
python scripts/og_image.py
```

Expected: `wrote C:\Users\Tejas\dota-mmr-shift\og-image.png`. Open the PNG with the Read tool and confirm three cards with Crusader `1,379,700`, Archon `1,222,200`, Legend `929,600`.

- [ ] **Step 7: Check in the browser**

Reload. Expected: break-even shows `41.7%`, `+200` at 45%, `+500` at 50% for 35/25. Set gain to 40: `38.5%`, `+425`, `+750`. Set gain 25, loss 25: `50.0%`, `-250`, `0`. Click "Copy link to this view": "Copied." appears. Method section renders with four headings and links.

- [ ] **Step 8: Commit**

```powershell
git add index.html scripts/og_image.py og-image.png
git commit -m "Add break-even calculator, sources, share link, and OG image"
```

---

### Task 9: Full page verification pass

**Files:**
- No new files. Fix anything found in `index.html` and commit.

- [ ] **Step 1: Run the unit tests**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 15 tests` … `OK`.

- [ ] **Step 2: Verify no anchor comments remain**

Run: `Select-String -Path index.html -Pattern "@timeline|@trend|@opendota|@breakeven|@method|@og|@init|@renderAll"`
Expected: no output.

- [ ] **Step 3: Browser checklist at desktop width**

With `python -m http.server 8765` running, open `http://localhost:8765/?month=2026-06` and confirm each item via `browser_snapshot` / `browser_take_screenshot`:

1. Headline cards: Crusader `1,379,700` / `+1,400`; Archon `1,222,200` / `+65,800`; Legend `929,600` / `+79,100`.
2. Slider opens on Jun 2026; the bar chart title reads "… — Jun 2026".
3. Press Play; it advances to Aug 2026 and the button returns to "Play". URL now ends `?month=2026-08`.
4. "36 stars" shows 36 bars; "8 medals" returns to 8.
5. Trend chart: three lines, legend with three names, red dashed marker, hover title on last Archon point reads `Archon · Aug 2026 · 17.46% · 1,222,200 players`.
6. Change-by-bracket table visible with Now + 1-day + since-Aug-2026 + since-Jan-2025 columns, Legend since-Aug delta green and above +190,000, Herald red. OpenDota today section visible with 8 bars. Snapshot trend visible with six points per line. Sparklines absent.
6b. Headline medal table: Herald row reads June `990,500` → Aug `856,100`, change `−134,400`, `−1.92 pt`; Immortal row change `+0.03 pt`.
7. Break-even defaults 35/25 → `41.7%`.
8. Population 10,000,000 → Crusader `1,971,000`, Archon `1,746,000`, Legend `1,328,000`; trend hover counts scale accordingly.
9. No console errors: `browser_cdp Runtime.evaluate` of `performance.getEntriesByType("resource").filter(e=>e.responseStatus>=400).length` returns `0`.

- [ ] **Step 4: Browser checklist at 360px**

Use `browser_cdp` `Emulation.setDeviceMetricsOverride` with `{width:360,height:800,deviceScaleFactor:1,mobile:true}`, reload, screenshot. Expected: cards stack in one column, controls wrap, bar chart and SVG fit the width with no horizontal scroll (`document.documentElement.scrollWidth <= 360` via `Runtime.evaluate`). Clear with `Emulation.clearDeviceMetricsOverride`.

- [ ] **Step 5: Commit any fixes**

```powershell
git add index.html
git commit -m "Fix issues found in verification pass"
```

(Skip if nothing changed.)

---

### Task 10: Publish: GitHub repo, Pages, first cron run

**Files:**
- None new.

- [ ] **Step 1: Create the GitHub repo and push**

Run:

```powershell
gh repo create dota-mmr-shift --public --source . --remote origin --push --description "How Dota 2 medal populations moved after the June 2026 MMR gain change"
```

Expected: repo URL printed; `git remote -v` shows `origin`.

- [ ] **Step 2: Enable GitHub Pages from main root**

Run:

```powershell
$login = gh api user -q .login
gh api -X POST "repos/$login/dota-mmr-shift/pages" -f build_type=legacy -f "source[branch]=main" -f "source[path]=/"
```

Expected: JSON with `"status": "building"` or similar. If it returns 409 (already exists), that is fine.

- [ ] **Step 3: Trigger the first snapshot**

Run:

```powershell
gh workflow run snapshot.yml
Start-Sleep -Seconds 90
gh run list --workflow snapshot.yml --limit 1
```

Expected: the latest run shows `completed success`. Then `git pull` and confirm `data/opendota.json` has one entry.

- [ ] **Step 4: Confirm the live page**

Run: `gh api "repos/$login/dota-mmr-shift/pages" -q .html_url`
Open the printed URL in the Cursor browser. Expected: same content as local, OpenDota today bar visible, `og-image.png` loads at `<url>/og-image.png`.

- [ ] **Step 5: Verify link unfurl metadata**

Run: `curl.exe -s "<pages url>" | Select-String "og:image"`
Expected: the absolute `og-image.png` URL matching the Pages host.

Done. Share the Pages URL (optionally with `?month=2026-06` to open on the "before" frame).
