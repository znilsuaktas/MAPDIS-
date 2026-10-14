import json
import pytest
from mapdis_research.config import load_config
from mapdis_research.processing import process, canonical_url
from mapdis_research.sources import discover, abstract_from_index
from mapdis_research.report import write_outputs
from mapdis_research.http import Client
from mapdis_research.__main__ import main


def rec(**overrides):
    return dict(dict(title="Oil spill observed", date="2024-03-01", url="https://example.org/a", text="SAR imagery identified an oil spill. Further validation needed.", doi="10.123/a", source="crossref", source_quality=0.8), **overrides)


def test_dedup_ranking_dates():
    config = {"keywords": ["oil spill", "SAR imagery"], "date_from": "2020-01-01"}
    results = process([rec(), rec(doi="https://doi.org/10.123/A", url="https://other.org/x"), rec(doi=None, date=None), rec(doi="10.123/b", url="https://example.org/b", title="irrelevant", text="")], config)
    assert len(results) == 1
    assert results[0]["keyword_matches"] == config["keywords"]
    assert "identified an oil spill" in results[0]["supporting_excerpt"]


def test_canonical_url():
    assert canonical_url("https://EXAMPLE.org/a/?utm_source=x&b=2#section") == "https://example.org/a?b=2"


def test_config_validation(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"keywords": ["oil"], "date_from": "2025-01-01", "date_to": "2020-01-01"}))
    with pytest.raises(ValueError):
        load_config(p)


def test_abstract():
    assert abstract_from_index({"spill": [1], "Oil": [0]}) == "Oil spill"


class Response:
    headers = {"Content-Type": "text/html"}
    url = "https://example.org/"
    text = '<html><h1>Oil spill</h1><meta property="article:published_time" content="2024-05-01"><article>Oil spill reported.</article></html>'


class FakeClient:
    def allowed(self, url):
        return True
    def get(self, url, **kwargs):
        return Response()


def test_public_extraction_and_terms():
    source = {"type": "website", "url": "https://example.org/"}
    with pytest.raises(PermissionError):
        discover(FakeClient(), {}, source)
    results = discover(FakeClient(), {}, dict(source, terms_reviewed=True))
    assert results[0]["date"] == "2024-05-01"
    assert results[0]["text"] == "Oil spill reported."


def test_robots_deny_and_fail_closed(monkeypatch):
    client = Client({"request_interval_seconds": 0.1})
    monkeypatch.setattr("mapdis_research.http.time.sleep", lambda _: None)
    class RobotsResponse:
        status_code = 200
        is_redirect = False
        headers = {"Content-Type": "text/plain"}
        text = "User-agent: *\nDisallow: /private\nCrawl-delay: 4"
        def raise_for_status(self):
            pass
    monkeypatch.setattr(client.session, "get", lambda *a, **k: RobotsResponse())
    assert not client.allowed("https://example.org/private/data")
    assert client.allowed("https://example.org/public")
    assert client.interval == 4
    import requests
    def fail(*a, **k):
        raise requests.ConnectionError()
    monkeypatch.setattr(client.session, "get", fail)
    assert not client.allowed("https://unavailable.org/a")


def test_outputs_citations_and_csv(tmp_path):
    results = process([rec()], {"keywords": ["oil spill"]})
    write_outputs(results, tmp_path, [{"source": "crossref", "status": "success", "count": 1}])
    assert json.loads((tmp_path / "results.json").read_text())[0]["doi"] == "10.123/a"
    assert "Citation: <https://example.org/a>" in (tmp_path / "report.md").read_text()
    assert "supporting_excerpt" in (tmp_path / "results.csv").read_text(encoding="utf-8-sig")


def test_cli_partial_failure(tmp_path, monkeypatch):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"keywords": ["oil spill"], "sources": [{"type": "crossref"}]}))
    def fail(*a):
        raise RuntimeError("unavailable")
    monkeypatch.setattr("mapdis_research.__main__.discover", fail)
    assert main(["run", "--config", str(p), "--output", str(tmp_path / "out")]) == 1
    assert json.loads((tmp_path / "out/run.json").read_text())[0]["status"] == "failed"


@pytest.mark.parametrize("kind", ["openalex", "crossref"])
def test_api_adapters(kind):
    class APIResponse:
        def json(self):
            if kind == "openalex":
                return {"results": [{"id": "https://openalex.org/W1", "display_name": "Oil spill", "publication_date": "2024-01-01", "doi": "https://doi.org/10.123/a", "abstract_inverted_index": {"Oil": [0], "spill": [1]}}]}
            return {"message": {"items": [{"title": ["Oil spill"], "DOI": "10.123/a", "URL": "https://doi.org/10.123/a", "published": {"date-parts": [[2024, 1, 1]]}, "abstract": "<p>Oil spill</p>"}]}}
    class APIClient:
        def get(self, url, **kwargs):
            assert kwargs["params"]["filter"]
            return APIResponse()
    records = discover(APIClient(), {"keywords": ["oil spill"], "date_from": "2020-01-01"}, {"type": kind})
    assert records[0]["text"] == "Oil spill"
    assert records[0]["date"] == "2024-01-01"


def test_successful_cli_end_to_end(tmp_path, monkeypatch):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"keywords": ["oil spill"], "sources": [{"type": "crossref"}]}))
    monkeypatch.setattr("mapdis_research.__main__.discover", lambda *a: [rec()])
    assert main(["run", "--config", str(p), "--output", str(tmp_path / "out")]) == 0
    data = json.loads((tmp_path / "out/results.json").read_text())
    assert len(data) == 1
    assert data[0]["url"] in (tmp_path / "out/report.md").read_text()


def test_header_title_and_robots_denial():
    class HeaderResponse(Response):
        text = '<header><h1>Oil spill headline</h1></header><main>Public evidence</main>'
    class HeaderClient(FakeClient):
        def get(self, *a, **k):
            return HeaderResponse()
    source = {"type": "website", "url": "https://example.org/", "terms_reviewed": True}
    assert discover(HeaderClient(), {}, source)[0]["title"] == "Oil spill headline"
    class DeniedClient(FakeClient):
        def allowed(self, url):
            return False
        def get(self, *a, **k):
            raise AssertionError("Denied page must not be fetched")
    assert discover(DeniedClient(), {}, source) == []


def test_duplicate_alias_bridge():
    records = [rec(), rec(doi="10.123/b", url="https://example.org/b"), rec(doi="10.123/a", url="https://example.org/b")]
    assert len(process(records, {"keywords": ["oil spill"]})) == 1
