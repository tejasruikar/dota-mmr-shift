# OpenDota-only MMR shift page

Date: 2026-10-01

## Source

Only `https://api.opendota.com/api/distributions`. Live fetch on page load (1 call).
Daily GitHub Action appends `data/opendota.json` (1 call/day). No Stratz, no Esports Tales.

Free OpenDota API: 60 calls/minute, 3,000/day, no key. This project stays far under that.

## Before vs after

Change date: 2026-06-18.

- **Before:** latest saved snapshot with `date < 2026-06-18` (currently 2025-01-25). There is no OpenDota capture in June 2026.
- **After:** live fetch, falling back to the latest saved snapshot.

Overlay grouped bar chart: 8 medals, share of public profiles (%). Two series: before and today.

## Day-to-day change

From the saved snapshots plus live (if its date is new): for each consecutive pair whose dates are exactly 1 day apart, plot Crusader, Archon, and Legend change in share (percentage points). The series starts when daily snapshots exist (30 Sep → 1 Oct 2026 onward). Sparse gaps (months) are not interpolated.

## Share over time

Line chart of Crusader, Archon, Legend share across all snapshots (x proportional to date), with a marker at 18 Jun 2026. This is the long view; it is not daily.

## Also on the page

Headline cards and an 8-medal table: live counts vs the before snapshot. Live change table (1 day / 7 day / 30 day / since 2 Aug 2026 / since 25 Jan 2025). Break-even calculator. Method note that June–July 2026 cannot be reconstructed.
