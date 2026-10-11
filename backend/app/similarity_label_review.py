"""Export candidate pairs for human labeling and validate reviewed labels."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

def _validated_website_url(value: Any, line: int, field: str) -> tuple[str, str]:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError(
            f"Line {line}: {field} must be an absolute HTTP(S) URL without embedded credentials"
        )
    host = parsed.hostname.lower().rstrip(".").removeprefix("www.")
    return url, host


FIELDS = [
    "source_name", "source_category", "source_description", "source_url",
    "candidate_name", "candidate_category", "candidate_description", "candidate_url",
    "label", "reviewer", "reviewed_at", "review_notes",
]


def export_review_csv(pairs: list[dict[str, Any]], output_path: str | Path) -> int:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for pair in pairs:
            row = {key: pair.get(key, "") for key in FIELDS}
            row["label"] = ""  # Labels must be assigned by a human.
            row["reviewer"] = ""
            row["reviewed_at"] = ""
            row["review_notes"] = ""
            writer.writerow(row)
            count += 1
    return count


def import_reviewed_csv(input_path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    with open(input_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = set(FIELDS)
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"Review CSV must include columns: {', '.join(FIELDS)}")
        for line, raw in enumerate(reader, start=2):
            label_text = (raw.get("label") or "").strip()
            if label_text not in {"0", "1"}:
                raise ValueError(f"Line {line}: label must be human-assigned 0 or 1")
            if not (raw.get("reviewer") or "").strip():
                raise ValueError(f"Line {line}: reviewer is required")
            if not (raw.get("reviewed_at") or "").strip():
                raise ValueError(f"Line {line}: reviewed_at is required")
            source_name = (raw.get("source_name") or "").strip()
            candidate_name = (raw.get("candidate_name") or "").strip()
            if not source_name or not candidate_name:
                raise ValueError(f"Line {line}: source_name and candidate_name are required")
            source_url, source_host = _validated_website_url(raw.get("source_url"), line, "source_url")
            candidate_url, candidate_host = _validated_website_url(
                raw.get("candidate_url"), line, "candidate_url"
            )
            if source_host == candidate_host:
                raise ValueError(f"Line {line}: a website cannot be compared with itself (same hostname)")
            key = tuple(sorted((source_host, candidate_host)))
            if key in seen:
                raise ValueError(f"Line {line}: duplicate website pair")
            seen.add(key)
            rows.append({
                "source_name": source_name,
                "source_url": source_url,
                "source_category": (raw.get("source_category") or "").strip(),
                "source_description": (raw.get("source_description") or "").strip(),
                "candidate_name": candidate_name,
                "candidate_url": candidate_url,
                "candidate_category": (raw.get("candidate_category") or "").strip(),
                "candidate_description": (raw.get("candidate_description") or "").strip(),
                "label": int(label_text),
                "provenance": "human_reviewed",
                "reviewer": (raw.get("reviewer") or "").strip(),
                "reviewed_at": (raw.get("reviewed_at") or "").strip(),
                "review_notes": (raw.get("review_notes") or "").strip()[:1000],
            })
    if not rows:
        raise ValueError("No reviewed pairs found.")
    if {row["label"] for row in rows} != {0, 1}:
        raise ValueError("Reviewed dataset must include both positive (1) and negative (0) pairs.")
    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\\n" for row in rows),
                    encoding="utf-8")
