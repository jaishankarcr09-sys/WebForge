from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.similarity_label_review import export_review_csv  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Export candidate pairs as an unlabeled review CSV.")
    parser.add_argument("--input", default="backend/data/pairs_for_review.jsonl")
    parser.add_argument("--output", default="backend/data/pairs_for_review.csv")
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    count = export_review_csv(rows, args.output)
    print(json.dumps({"exported_unlabeled_pairs": count, "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
