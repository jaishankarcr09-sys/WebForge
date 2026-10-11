import unittest

from app.similarity_dataset_quality import audit_dataset


def row(i, label):
    return {
        "source_url": f"https://source{i}.example.org",
        "candidate_url": f"https://candidate{i}.example.net",
        "label": label,
        "reviewer": "reviewer-1",
        "reviewed_at": "2026-10-11",
        "review_status": "human_reviewed",
    }


class SimilarityDatasetQualityTests(unittest.TestCase):
    def test_accepts_clean_reviewed_dataset(self):
        rows = [row(i, 1 if i < 15 else 0) for i in range(30)]
        report = audit_dataset(rows)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["rows"], 30)
        self.assertEqual(report["distinct_source_domains"], 30)

    def test_rejects_unreviewed_or_missing_labels(self):
        rows = [row(i, 1 if i % 2 else 0) for i in range(30)]
        rows[0]["label"] = None
        rows[1]["reviewer"] = ""
        report = audit_dataset(rows)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("invalid binary labels" in error for error in report["errors"]))
        self.assertTrue(any("reviewer" in error for error in report["errors"]))

    def test_rejects_self_pairs_and_duplicate_unordered_pairs(self):
        rows = [row(i, 1 if i % 2 else 0) for i in range(30)]
        rows[0]["candidate_url"] = rows[0]["source_url"]
        rows[1]["source_url"], rows[1]["candidate_url"] = rows[2]["candidate_url"], rows[2]["source_url"]
        report = audit_dataset(rows)
        self.assertEqual(report["status"], "fail")
        self.assertGreaterEqual(report["self_pairs"], 1)
        self.assertGreaterEqual(report["duplicate_unordered_pairs"], 1)

    def test_warns_when_data_is_too_small(self):
        report = audit_dataset([row(1, 1), row(2, 0)])
        self.assertEqual(report["status"], "pass")
        self.assertTrue(any("Only 2 pairs" in warning for warning in report["warnings"]))

    def test_rejects_invalid_urls_and_single_class(self):
        rows = [row(i, 1) for i in range(30)]
        rows[0]["source_url"] = "not-a-url"
        report = audit_dataset(rows)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any("Both positive" in error for error in report["errors"]))
        self.assertGreaterEqual(report["rows_missing_valid_urls"], 1)


if __name__ == "__main__":
    unittest.main()
