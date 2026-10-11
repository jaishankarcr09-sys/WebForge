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


def test_public_url_guard_rejects_local_and_private_targets(monkeypatch):
    from app.public_metadata import is_public_http_url

    assert not is_public_http_url("http://127.0.0.1/admin")
    assert not is_public_http_url("http://[::1]/admin")
    assert not is_public_http_url("http://localhost/")
    assert not is_public_http_url("http://user:secret@example.com/")


def test_public_url_guard_rejects_hostnames_resolving_to_private_ip(monkeypatch):
    import socket
    from app.public_metadata import is_public_http_url

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 80)),
    ])
    assert not is_public_http_url("http://internal.example/")


def test_collector_does_not_follow_redirect_to_private_network(monkeypatch):
    import socket
    from app.public_metadata import collect_one

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
    ])

    class Response:
        def __init__(self, status_code, text="", headers=None, url=""):
            self.status_code = status_code
            self.text = text
            self.headers = headers or {}
            self.url = url

    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            if url.endswith("/robots.txt"):
                return Response(200, "User-agent: *\\nAllow: /")
            return Response(302, headers={"location": "http://127.0.0.1:8080/admin"}, url=url)

    session = Session()
    result = collect_one("https://public.example/", session=session)
    assert result["status"] == "rejected"
    assert "redirect target" in result["reason"]
    assert not any("127.0.0.1" in url for url, _ in session.calls)
    assert all(kwargs.get("allow_redirects") is False for _, kwargs in session.calls)
