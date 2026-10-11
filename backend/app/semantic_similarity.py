"""Optional semantic-embedding baseline for website similarity.

Uses a pretrained SentenceTransformer as a zero-shot baseline; it is NOT fine-tuned
on WebForge labels. Keep it optional so ordinary backend installs do not download a
large model. Evaluate on human-labeled held-out pairs before using in production.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Protocol

import numpy as np


class Encoder(Protocol):
    def encode(self, sentences: list[str], **kwargs: Any) -> Any: ...


def website_text(row: dict[str, Any], prefix: str) -> str:
    fields = ("name", "category", "description")
    values = [str(row.get(f"{prefix}_{field}") or "").strip() for field in fields]
    text = " | ".join(value for value in values if value)
    if not text:
        raise ValueError(f"Missing website metadata for {prefix}.")
    return text


def cosine_scores(left: Any, right: Any) -> np.ndarray:
    """Return pairwise row-wise cosine scores for equally shaped matrices."""
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.ndim != 2 or b.ndim != 2 or a.shape != b.shape:
        raise ValueError("Embedding matrices must have identical 2D shapes.")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Embeddings must contain only finite values.")
    a_norm = np.linalg.norm(a, axis=1)
    b_norm = np.linalg.norm(b, axis=1)
    denominator = a_norm * b_norm
    if np.any(denominator == 0):
        raise ValueError("Cannot score zero-vector embeddings.")
    scores = np.sum(a * b, axis=1) / denominator
    return np.clip(scores, -1.0, 1.0)


def score_pairs(records: list[dict[str, Any]], encoder: Encoder,
                batch_size: int = 32) -> list[dict[str, Any]]:
    """Score labeled or unlabeled source/candidate records using embedding cosine."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")
    if not records:
        return []
    left_texts = [website_text(row, "source") for row in records]
    right_texts = [website_text(row, "candidate") for row in records]
    left_embeddings = encoder.encode(left_texts, batch_size=batch_size, normalize_embeddings=False)
    right_embeddings = encoder.encode(right_texts, batch_size=batch_size, normalize_embeddings=False)
    scores = cosine_scores(left_embeddings, right_embeddings)
    output = []
    for row, score in zip(records, scores):
        item = dict(row)
        item["score"] = round(float(score), 8)
        item["scoring_model"] = "sentence-transformers/all-MiniLM-L6-v2"
        item["scoring_method"] = "embedding_cosine_zero_shot"
        output.append(item)
    return output


def load_encoder(model_name: str) -> Encoder:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Optional dependency missing. Install it with: pip install sentence-transformers"
        ) from exc
    return SentenceTransformer(model_name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="JSONL source/candidate records")
    parser.add_argument("--output", default="backend/data/semantic_scored_pairs.jsonl")
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    records = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    encoder = load_encoder(args.model)
    scored = score_pairs(records, encoder, batch_size=args.batch_size)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in scored), encoding="utf-8")
    print(json.dumps({
        "scored_pairs": len(scored),
        "model": args.model,
        "method": "zero_shot_embedding_cosine",
        "fine_tuned_on_webforge_labels": False,
        "output": str(output),
        "warning": "Scores are ranking signals, not calibrated probabilities or accuracy claims. Evaluate on a held-out, human-labeled dataset.",
    }, indent=2))


if __name__ == "__main__":
    main()
