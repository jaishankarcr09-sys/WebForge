import csv

import pytest

from app.similarity_label_review import export_review_csv, import_reviewed_csv


def test_export_always_blanks_labels(tmp_path):
    path = tmp_path / "review.csv"
    count = export_review_csv([{"source_name":"A","candidate_name":"B","label":1}], path)
    assert count == 1
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["label"] == ""
    assert row["reviewer"] == ""


def _write_csv(path, rows):
    fields = ["source_name","source_category","source_description","source_url",
              "candidate_name","candidate_category","candidate_description","candidate_url",
              "label","reviewer","reviewed_at","review_notes"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _row(a, b, label, **kwargs):
    return {"source_name":a,"source_category":"tools","source_description":a,
            "source_url":"","candidate_name":b,"candidate_category":"tools",
            "candidate_description":b,"candidate_url":"","label":str(label),
            "reviewer":"reviewer1","reviewed_at":"2026-10-11", "review_notes":"reviewed",**kwargs}


def test_import_accepts_both_human_labels_and_provenance(tmp_path):
    path = tmp_path / "reviewed.csv"
    _write_csv(path, [_row("A","B",1), _row("C","D",0)])
    rows = import_reviewed_csv(path)
    assert [r["label"] for r in rows] == [1,0]
    assert all(r["provenance"] == "human_reviewed" for r in rows)


def test_import_rejects_missing_label_or_reviewer(tmp_path):
    path = tmp_path / "reviewed.csv"
    _write_csv(path, [_row("A","B",""), _row("C","D",0)])
    with pytest.raises(ValueError, match="human-assigned"):
        import_reviewed_csv(path)


def test_import_rejects_duplicates_and_single_class(tmp_path):
    path = tmp_path / "reviewed.csv"
    _write_csv(path, [_row("A","B",1), _row("B","A",0)])
    with pytest.raises(ValueError, match="duplicate"):
        import_reviewed_csv(path)
    _write_csv(path, [_row("A","B",1), _row("C","D",1)])
    with pytest.raises(ValueError, match="both positive"):
        import_reviewed_csv(path)
