from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.similarity_label_review import import_reviewed_csv, write_jsonl  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Validate human labels and create training JSONL.")
    parser.add_argument("--input", required=True, help="CSV filled in by human reviewers")
    parser.add_argument("--output", default="backend/data/human_reviewed_similarity_pairs.jsonl")
    args = parser.parse_args()
    rows = import_reviewed_csv(args.input)
    write_jsonl(rows, args.output)
    print(json.dumps({
        "accepted_human_reviewed_pairs": len(rows),
        "positive_pairs": sum(row["label"] == 1 for row in rows),
        "negative_pairs": sum(row["label"] == 0 for row in rows),
        "output": args.output,
    }, indent=2))


if __name__ == "__main__":
    main()
