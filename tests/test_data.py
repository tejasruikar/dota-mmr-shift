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
            self.assertEqual(
                sorted(e["bins"]),
                sorted(f"{m}{s}" for m in range(1, 8) for s in range(1, 6)) + ["80"],
                e["date"],
            )


if __name__ == "__main__":
    unittest.main()
