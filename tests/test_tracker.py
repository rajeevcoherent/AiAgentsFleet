"""The run tracker (AllMarkets/markets_priority.csv): generated reports are labelled and never re-run."""
import csv

from AiAgentsFleet.cmi_report import tracker


def _write(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_sync_labels_existing_reports_and_marks(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "FLEET", tmp_path)
    done = tmp_path / "output" / "a-market" / "a-market-cmi-whitepaper.docx"
    done.parent.mkdir(parents=True)
    done.write_text("x")
    path = tmp_path / "t.csv"
    _write(path, [{"order": 1, "market": "A Market", "slug": "a-market"},
                  {"order": 2, "market": "B Market", "slug": "b-market"}])
    rows = tracker.load(path)
    assert [r["status"] for r in rows] == ["pending", "pending"]
    assert tracker.sync(rows) == 1 and rows[0]["status"] == "generated" and rows[0]["report"].endswith(".docx")
    tracker.mark(rows[1], "failed", 3.0)
    assert tracker.save(rows, path)
    again = tracker.load(path)
    assert [r["status"] for r in again] == ["generated", "failed"] and again[1]["minutes"] == "3.0"


def test_tracker_open_in_excel_goes_to_pending_file(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "FLEET", tmp_path)
    path = tmp_path / "t.csv"
    _write(path, [{"order": 1, "market": "A Market", "slug": "a-market"}])
    rows = tracker.load(path)
    tracker.mark(rows[0], "generated", 5.0)
    real_open = type(path).open

    def locked(self, mode="r", *a, **k):          # Excel holds the CSV open
        if self == path and "w" in mode:
            raise PermissionError
        return real_open(self, mode, *a, **k)
    monkeypatch.setattr(type(path), "open", locked)
    assert not tracker.save(rows, path)
    monkeypatch.setattr(type(path), "open", real_open)
    assert tracker.load(path)[0]["status"] == "generated"          # merged from the .pending.csv
