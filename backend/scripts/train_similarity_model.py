"""Train the WebForge website similarity baseline from reviewed JSONL pairs.

Run from the repository root:
  python -m pip install -r backend/requirements.txt
  python backend/scripts/train_similarity_model.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.similarity_model import train_model  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(ROOT / "backend/data/similarity_training_pairs.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "backend/models/similarity_baseline.joblib"))
    args = parser.parse_args()
    rows = []
    with open(args.data, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {line_number}: {exc}") from exc
            if row.get("label") not in (0, 1):
                raise SystemExit(f"Line {line_number}: label must be 0 or 1")
            rows.append(row)
    report = train_model(rows, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
