import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGE_DATE = "2026-06-18"


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

    def test_has_a_snapshot_before_the_mmr_change(self):
        before = [e for e in self.data if e["date"] < CHANGE_DATE]
        self.assertTrue(before)
        self.assertEqual(before[-1]["date"], "2025-01-25")

    def test_stratz_file_is_gone(self):
        self.assertFalse((ROOT / "data" / "stratz.json").exists())


if __name__ == "__main__":
    unittest.main()
