# Public metadata collection and pair labeling

## 1. Prepare an explicit seed list

Create a CSV you control with columns `url,category`, for example:

```csv
url,category
https://example.com/,general
https://www.python.org/,developer tools
```

The collector does not search for or recursively crawl every page. It only visits URLs in your input CSV, checks `robots.txt`, fails closed when robots cannot be checked, sends a descriptive user agent, requires a minimum 1-second per-host delay (default 2 seconds), and stores title, description, category, hostname, retrieval timestamp, URL, and provenance. It skips non-HTML and HTTP error responses. Always check the site's terms and applicable law; robots.txt is not a license to reuse copyrighted content.

## 2. Collect metadata

Run from the repository root:

```bash
python backend/scripts/collect_public_metadata.py --input backend/data/site_seeds.csv --output backend/data/public_site_metadata.jsonl --delay 2
```

No site body is written to the dataset. The collector is designed for a small, controlled seed list, not high-volume scraping.

## 3. Create a human-review queue

```bash
python backend/scripts/build_similarity_review_pairs.py --input backend/data/public_site_metadata.jsonl --output backend/data/pairs_for_review.jsonl
```

Pairs are intentionally created with `label: null`. Reviewers must label each pair (1 = similar website/product category and user need; 0 = not similar) and record reviewer/date/notes before moving it into the training dataset. Never convert search co-occurrence or category equality alone into a ground-truth positive label.

## 4. Training and evaluation gate

The current baseline trainer requires binary labels and will reject unlabeled review rows. Keep all pages/pairs from the same domain on a single side of the evaluation split to reduce leakage. Track precision/recall, PR-AUC where applicable, and ranking metrics such as precision@k and nDCG@k against human-reviewed judgments. Do not expose the raw classifier score as a similarity percentage or promote a model to production until held-out evaluation is satisfactory.

## Data limitations

The current seed dataset is small and curated. The collection pipeline is a controlled metadata acquisition tool; it does not magically create labels or train a foundation model on the entire web. Public websites may prohibit automated access or reuse; respect robots rules, terms, rate limits, privacy, and copyright.
