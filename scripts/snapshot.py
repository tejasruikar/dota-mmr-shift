"""Append today's OpenDota rank distribution to data/opendota.json.

Run by .github/workflows/snapshot.yml daily. Safe to rerun: one entry per date.
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
