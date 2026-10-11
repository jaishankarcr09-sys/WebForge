"""Safe API-facing wrapper for the optional similarity ranking model.

The API only scores metadata supplied in the request. It does not fetch user-provided
URLs, and it never silently trains or loads the illustrative seed dataset in production.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .similarity_model import load_model, rank_candidates

MODEL_PATH_ENV = "WEBFORGE_SIMILARITY_MODEL_PATH"
_REQUIRED_TEXT_FIELDS = ("name", "category", "description")


def _normalize_site(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    site: dict[str, str] = {}
    for field in _REQUIRED_TEXT_FIELDS:
        raw = value.get(field, "")
        if not isinstance(raw, str):
            raise ValueError(f"{label}.{field} must be text.")
        site[field] = raw.strip()
    if not site["name"]:
        raise ValueError(f"{label}.name is required.")
    if not (site["category"] or site["description"]):
        raise ValueError(f"{label} must include a category or description.")
    return site


def model_status(model_path: str | None = None) -> dict[str, Any]:
    configured = (model_path if model_path is not None else os.getenv(MODEL_PATH_ENV, "")).strip()
    exists = bool(configured) and Path(configured).is_file()
    return {
        "feature": "website_similarity_ranking",
        "status": "ready" if exists else "model_not_configured",
        "model_configured": bool(configured),
        "model_artifact_exists": exists,
        "model_version": None,
        "note": (
            "Scores are ranking signals, not probabilities that two businesses are identical."
            if exists else
            "No trained model artifact is configured. Collect and review examples, evaluate the model, "
            "then configure WEBFORGE_SIMILARITY_MODEL_PATH before enabling ranking."
        ),
    }


def rank_metadata(payload: Any, model_path: str | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be an object.")
    source = _normalize_site(payload.get("source"), "source")
    candidates_raw = payload.get("candidates")
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise ValueError("candidates must be a non-empty list.")
    if len(candidates_raw) > 50:
        raise ValueError("A maximum of 50 candidates can be ranked per request.")
    candidates = [_normalize_site(item, f"candidates[{index}]")
                  for index, item in enumerate(candidates_raw)]
    source_key = source["name"].casefold()
    if any(item["name"].casefold() == source_key for item in candidates):
        raise ValueError("A website cannot be compared with itself.")
    configured = (model_path if model_path is not None else os.getenv(MODEL_PATH_ENV, "")).strip()
    if not configured or not Path(configured).is_file():
        raise FileNotFoundError("A trained similarity model is not configured.")
    model = load_model(configured)
    source_record = {f"source_{key}": value for key, value in source.items()}
    candidate_records = [
        {f"candidate_{key}": value for key, value in item.items()}
        for item in candidates
    ]
    ranked = rank_candidates(model, source_record, candidate_records)
    return {
        "model_version": model.get("model_version", "unknown"),
        "score_semantics": "ranking_signal_not_identity_probability",
        "results": [
            {
                "name": row["candidate_name"],
                "category": row["candidate_category"],
                "description": row["candidate_description"],
                "score": round(float(row["model_similarity_score"]), 6),
                "model_version": row["similarity_model_version"],
            }
            for row in ranked
        ],
    }
