from app.public_metadata import parse_metadata
from app.pair_review import build_review_pairs


def test_metadata_parser_extracts_title_and_description_without_body():
    result = parse_metadata(
        '<html><head><title>Example Store</title><meta name="description" content="Products &amp; checkout"></head>'
        '<body><p>Private account details should not be stored</p></body></html>',
        "https://example.com", "ecommerce",
    )
    assert result["title"] == "Example Store"
    assert result["description"] == "Products & checkout"
    assert result["category"] == "ecommerce"
    assert "Private account details" not in str(result)
    assert result["provenance"] == "public_metadata_single_page"


def test_pair_builder_never_assigns_labels_and_avoids_same_host():
    records = [
        {"status":"collected","url":"https://a.example/","hostname":"a.example","title":"A","description":"shop","category":"commerce"},
        {"status":"collected","url":"https://a.example/about","hostname":"a.example","title":"A About","description":"about","category":"commerce"},
        {"status":"collected","url":"https://b.example/","hostname":"b.example","title":"B","description":"shop","category":"commerce"},
        {"status":"skipped","url":"https://c.example/","hostname":"c.example","title":"C","description":"ignored","category":"commerce"},
    ]
    pairs = build_review_pairs(records)
    assert len(pairs) == 1
    assert pairs[0]["label"] is None
    assert pairs[0]["review_status"] == "needs_human_label"
    assert pairs[0]["source_url"] != pairs[0]["candidate_url"]


def test_pair_builder_respects_max_pairs():
    records = [
        {"status":"collected","url":f"https://{name}.example/","hostname":f"{name}.example","title":name,
         "description":f"{name} platform","category":"tools"}
        for name in ["a","b","c","d"]
    ]
    assert len(build_review_pairs(records, max_pairs=2)) == 2
