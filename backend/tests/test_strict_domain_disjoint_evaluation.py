from app.strict_domain_disjoint_evaluation import (
    build_strict_splits,
    partition_pair_indices,
)


def _row(source, candidate, label=0):
    return {
        "source_name": source,
        "source_category": "software",
        "source_description": f"{source} product",
        "source_url": f"https://{source}.example/",
        "candidate_name": candidate,
        "candidate_category": "software",
        "candidate_description": f"{candidate} product",
        "candidate_url": f"https://{candidate}.example/",
        "label": label,
    }


def test_partition_excludes_cross_partition_pairs():
    rows = [
        _row("alpha", "beta", 0),
        _row("alpha", "gamma", 1),
        _row("delta", "epsilon", 0),
        _row("beta", "delta", 1),
    ]
    train, test, excluded = partition_pair_indices(
        rows,
        train_domains={"alpha.example", "beta.example"},
        test_domains={"delta.example", "epsilon.example"},
    )
    assert train == [0]
    assert test == [2]
    assert excluded == [1, 3]


def test_partition_rejects_overlapping_domain_sets():
    rows = [_row("alpha", "beta")]
    try:
        partition_pair_indices(
            rows,
            train_domains={"alpha.example"},
            test_domains={"alpha.example", "beta.example"},
        )
    except ValueError as exc:
        assert "must be disjoint" in str(exc)
    else:
        raise AssertionError("Expected overlapping domain sets to be rejected")


def test_strict_splits_have_no_domain_overlap_and_exclude_cross_pairs():
    # 9 domains yield 36 unique pairs; alternating labels gives both classes.
    domains = [f"site{i}" for i in range(9)]
    rows = []
    for i, source in enumerate(domains):
        for j in range(i + 1, len(domains)):
            rows.append(_row(source, domains[j], (i + j) % 2))

    splits = build_strict_splits(rows, n_splits=30, test_size=0.33, random_state=7)
    assert splits
    for split in splits:
        assert set(split["train_domains"]).isdisjoint(split["test_domains"])
        assert split["train_indices"]
        assert split["test_indices"]
        assert split["excluded_indices"]
        train_domains = set(split["train_domains"])
        test_domains = set(split["test_domains"])
        for index in split["train_indices"]:
            row = rows[index]
            assert row["source_url"].split("//")[1].split("/")[0] in train_domains
            assert row["candidate_url"].split("//")[1].split("/")[0] in train_domains
        for index in split["test_indices"]:
            row = rows[index]
            assert row["source_url"].split("//")[1].split("/")[0] in test_domains
            assert row["candidate_url"].split("//")[1].split("/")[0] in test_domains
