"""Lightweight, trainable website-pair similarity model.

This is an initial supervised ranking baseline, not an internet-scale foundation model.
It learns from reviewed positive/negative website pairs and returns a ranking signal,
never a probability that two businesses are identical.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{2,}", (text or "").lower()))


def _text(record: dict[str, Any], prefix: str) -> str:
    return " ".join(
        str(record.get(f"{prefix}_{field}") or "")
        for field in ("name", "category", "description")
    ).strip()


def pair_features(source: dict[str, Any], candidate: dict[str, Any],
                  word_vectorizer: TfidfVectorizer,
                  char_vectorizer: TfidfVectorizer) -> np.ndarray:
    left, right = _text(source, "source"), _text(candidate, "candidate")
    word = word_vectorizer.transform([left, right])
    char = char_vectorizer.transform([left, right])
    a, b = _tokens(left), _tokens(right)
    union = a | b
    intersection = a & b
    category_a = str(source.get("source_category") or "").strip().lower()
    category_b = str(candidate.get("candidate_category") or "").strip().lower()
    jaccard = len(intersection) / len(union) if union else 0.0
    containment = len(intersection) / min(len(a), len(b)) if a and b else 0.0
    category_match = float(bool(category_a and category_b and category_a == category_b))
    return np.asarray([[
        float(cosine_similarity(word[0], word[1])[0, 0]),
        float(cosine_similarity(char[0], char[1])[0, 0]),
        jaccard,
        containment,
        category_match,
    ]], dtype=float)


def train_model(records: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
    if len(records) < 8:
        raise ValueError("At least 8 reviewed website pairs are required.")
    labels = np.asarray([int(row["label"]) for row in records], dtype=int)
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("Training data must include both similar (1) and dissimilar (0) pairs.")

    texts = [_text(row, "source") for row in records] + [
        _text(row, "candidate") for row in records
    ]
    word_vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=12000)
    char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=18000)
    word_vectorizer.fit(texts)
    char_vectorizer.fit(texts)

    features = np.vstack([
        pair_features(row, row, word_vectorizer, char_vectorizer)
        for row in records
    ])
    classifier = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    classifier.fit(features, labels)
    artifact = {
        "model_version": "webforge-similarity-baseline-1",
        "feature_names": ["word_tfidf_cosine", "character_tfidf_cosine", "token_jaccard",
                          "token_containment", "category_match"],
        "word_vectorizer": word_vectorizer,
        "char_vectorizer": char_vectorizer,
        "classifier": classifier,
        "training_rows": len(records),
        "positive_rows": int(labels.sum()),
        "negative_rows": int((labels == 0).sum()),
        "training_data_scope": "curated_seed_pairs",
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path)
    return {
        "model_version": artifact["model_version"],
        "training_rows": len(records),
        "positive_rows": artifact["positive_rows"],
        "negative_rows": artifact["negative_rows"],
        "artifact_path": str(path),
    }


def load_model(path: str | Path) -> dict[str, Any]:
    return joblib.load(path)


def score_pair(model: dict[str, Any], source: dict[str, Any],
               candidate: dict[str, Any]) -> float:
    features = pair_features(source, candidate, model["word_vectorizer"], model["char_vectorizer"])
    return float(model["classifier"].predict_proba(features)[0, 1])


def rank_candidates(model: dict[str, Any], source: dict[str, Any],
                    candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for candidate in candidates:
        ranked.append({**candidate, "model_similarity_score": score_pair(model, source, candidate),
                       "similarity_model_version": model["model_version"]})
    return sorted(ranked, key=lambda row: row["model_similarity_score"], reverse=True)
