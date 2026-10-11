# WebForge similarity-model training

## First model: transparent baseline

The first dedicated model is a supervised website-pair classifier built from word and character TF-IDF similarity, token overlap, and website-category agreement. It is trained with logistic regression and is intended to rank candidate websites for review. It does **not** claim to measure a universal percentage of business similarity, and its score is not a probability that two companies or products are identical.

## Train locally

```bash
python -m pip install -r backend/requirements.txt
python backend/scripts/train_similarity_model.py
```

The command reads `backend/data/similarity_training_pairs.jsonl` and writes `backend/models/similarity_baseline.joblib`. The artifact is generated locally and should not be committed; it is excluded by `.gitignore`.

## Data scope and limitations

The checked-in dataset is a small, manually curated seed set with explicit binary labels and `curated_seed` provenance. It is sufficient to prove the end-to-end training and inference pipeline, **not** to claim production-grade accuracy or that a model was trained on the whole web. Do not use the model score as a public percentage until a representative, reviewed dataset and held-out evaluation establish calibration and ranking quality.

## Next training-data phase

Collect only publicly accessible metadata under applicable terms and robots/access policies; keep URL, retrieval time, source/provenance, category, title, description, and extraction status. Do not store full page bodies by default. Add human-reviewed positive/negative pairs, split evaluation by website/domain to reduce leakage, report ranking metrics, and retrain versioned artifacts. Search discovery remains necessary for finding new candidate sites; the trained model ranks candidates rather than replacing web search.

## Current scope

This PR only introduces the model-training pipeline and seed dataset. It does not yet connect the model to the live Similar Websites UI, the voice agent, speech services, or animated interactions.
