from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.similarity_label_review import import_reviewed_csv, write_jsonl  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Validate human-reviewed similarity labels and write JSONL.")
    parser.add_argument("--input", default="backend/data/saas_similarity_pilot_review.csv")
    parser.add_argument("--output", default="backend/data/saas_similarity_pilot_human_reviewed.jsonl")
    args = parser.parse_args()
    rows = import_reviewed_csv(args.input)
    write_jsonl(rows, args.output)
    print(json.dumps({
        "validated_human_reviewed_pairs": len(rows),
        "output": args.output,
        "labels_assigned_automatically": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
