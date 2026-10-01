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
        self.assertEqual(
            [e["date"] for e in snapshot.append(existing, older)],
            ["2026-10-05", "2026-10-12"],
        )


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
            rc = snapshot.main(
                path=path,
                fetch_fn=lambda: (SAMPLE_ROWS, SAMPLE_TOTAL),
                today="2026-10-05",
            )
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
