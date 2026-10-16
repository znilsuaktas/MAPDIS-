"""API metadata discovery and explicitly approved public-page extraction."""
import logging
import requests
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def plain(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def abstract_from_index(index):
    positions = sorted((pos, word) for word, offsets in (index or {}).items() for pos in offsets)
    return " ".join(word for _, word in positions)


def record(title, published, url, text, doi, source, quality):
    return dict(title=plain(title), date=published, url=url, text=plain(text), doi=doi,
                source=source, source_quality=quality)


def discover(client, config, source):
    limit = config.get("max_results_per_source", 10)
    quality = source.get("quality", 0.5)
    kind = source["type"]
    if kind == "website":
        if not source.get("terms_reviewed", False):
            raise PermissionError("Public website requires terms_reviewed=true after manual review")
        urls = [source["url"]]
        results = []
        seen = set()
        for url in urls:
            if len(results) >= limit:
                break
            if url in seen:
                continue
            seen.add(url)
            if not client.allowed(url):
                log.warning("robots.txt denies %s", url)
                continue
            response = client.get(url)
            if "text/html" not in response.headers.get("Content-Type", ""):
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.select('input[type="password"]'):
                log.warning("Login page skipped: %s", url)
                continue
            # Follow only same-origin links, with a strict finite budget.
            if url == source["url"]:
                for link in soup.select("a[href]"):
                    target = urljoin(response.url, link["href"]).split("#")[0]
                    if urlsplit(target).netloc == urlsplit(source["url"]).netloc and target.startswith("https://") and target not in urls:
                        urls.append(target)
                    if len(urls) >= limit:
                        break
            canonical = soup.select_one('link[rel="canonical"]')
            canonical_url = urljoin(response.url, canonical.get("href", "")) if canonical else response.url
            if urlsplit(canonical_url).netloc != urlsplit(response.url).netloc:
                canonical_url = response.url
            title = soup.select_one("h1") or soup.title
            date_tag = soup.select_one('meta[property="article:published_time"], meta[name="citation_publication_date"], time[datetime]')
            published = (date_tag.get("content") or date_tag.get("datetime")) if date_tag else None
            title_text = title.get_text() if title else "Untitled"
            for element in soup.select("script, style, nav, footer, header, form"):
                element.decompose()
            content = soup.select_one("article") or soup.select_one("main") or soup.body
            results.append(record(title_text, published[:10] if published else None,
                                  canonical_url, content.get_text(" ", strip=True) if content else "", None, "website", quality))
        return results
    results = []
    if not hasattr(client, "diagnostics"):
        client.diagnostics = []
    queries = config.get("queries", config["keywords"])[:config.get("max_queries", 100)]
    for keyword in queries:
        cursor = "*"
        previous_pages = set()
        for page in range(1, config.get("pages_per_query", 1) + 1):
            filters = []
            if kind == "openalex":
                endpoint = "https://api.openalex.org/works"
                params = {"search": keyword, "per-page": limit, "page": page}
                names = (("date_from", "from_publication_date"), ("date_to", "to_publication_date"))
            else:
                endpoint = "https://api.crossref.org/works"
                params = {"query": keyword, "rows": limit, "cursor": cursor}
                names = (("date_from", "from-pub-date"), ("date_to", "until-pub-date"))
            for key, prefix in names:
                if config.get(key):
                    filters.append(f"{prefix}:{config[key]}")
            if filters:
                params["filter"] = ",".join(filters)
            diagnostic = dict(source=kind, query=keyword, page=page)
            try:
                data = client.get(endpoint, params=params).json()
                items = data.get("results", []) if kind == "openalex" else data.get("message", {}).get("items", [])
                page_keys = tuple(str(item.get("DOI") or item.get("doi") or item.get("id") or item.get("URL") or item.get("title")) for item in items)
                if items and page_keys in previous_pages:
                    diagnostic.update(status="success", count=0, repeated_page=True)
                    client.diagnostics.append(diagnostic)
                    break
                previous_pages.add(page_keys)
                for item in items:
                    result = api_record(item, kind, quality)
                    result["discovery"] = [dict(source=kind, query=keyword, page=page)]
                    results.append(result)
                diagnostic.update(status="success", count=len(items))
                client.diagnostics.append(diagnostic)
                log.info("%s | query %s/%s | page %s | %s records", kind, queries.index(keyword)+1, len(queries), page, len(items))
                if not items or len(items) < limit:
                    break
                if kind == "crossref":
                    next_cursor = data.get("message", {}).get("next-cursor")
                    if not next_cursor:
                        break
                    # Crossref scroll cursors may legitimately remain unchanged.
                    # Stop on repeated result pages, not repeated cursor strings.
                    cursor = next_cursor
                # OpenAlex basic page pagination is supported without cursor credentials.
                # The configured maximum is 20*200=4000 records, below its 10000-record ceiling.
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                response = getattr(exc, "response", None)
                status_code = response.status_code if response is not None else None
                diagnostic.update(status="failed", error_type=type(exc).__name__, http_status=status_code)
                client.diagnostics.append(diagnostic)
                log.error("%s page failed (%s; HTTP %s); partial results retained", kind, type(exc).__name__, status_code)
                # Do not repeat requests after auth/rate-limit/transport failures.
                if status_code in {401, 403, 429} or isinstance(exc, (requests.ConnectionError, requests.Timeout)):
                    return results
                break
    return results


def api_record(item, kind, quality):
    if kind == "openalex":
        location = item.get("primary_location") or {}
        result = record(item.get("display_name", ""), item.get("publication_date"),
                        location.get("landing_page_url") or item.get("doi") or item["id"],
                        abstract_from_index(item.get("abstract_inverted_index")), item.get("doi"), kind, quality)
        result["authors"] = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
        result["journal"] = (location.get("source") or {}).get("display_name")
        result["publication_type"] = item.get("type")
    else:
        dates = (item.get("published") or {}).get("date-parts", [[]])[0]
        published = "-".join(str(n).zfill(2) if i else str(n) for i, n in enumerate(dates)) if len(dates) == 3 else None
        result = record((item.get("title") or [""])[0], published, item.get("URL", ""),
                        item.get("abstract", ""), item.get("DOI"), kind, quality)
        result["authors"] = [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in item.get("author", [])]
        result["journal"] = (item.get("container-title") or [None])[0]
        result["publication_type"] = item.get("type")
    return result
