"""API metadata discovery and explicitly approved public-page extraction."""
import logging
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
    for keyword in config["keywords"]:
        params = {}
        filters = []
        if kind == "openalex":
            endpoint = "https://api.openalex.org/works"
            params = {"search": keyword, "per-page": limit}
            for key, prefix in (("date_from", "from_publication_date"), ("date_to", "to_publication_date")):
                if config.get(key):
                    filters.append(f"{prefix}:{config[key]}")
        else:
            endpoint = "https://api.crossref.org/works"
            params = {"query": keyword, "rows": limit}
            for key, prefix in (("date_from", "from-pub-date"), ("date_to", "until-pub-date")):
                if config.get(key):
                    filters.append(f"{prefix}:{config[key]}")
        if filters:
            params["filter"] = ",".join(filters)
        data = client.get(endpoint, params=params).json()
        items = data.get("results", []) if kind == "openalex" else data.get("message", {}).get("items", [])
        for item in items:
            if kind == "openalex":
                location = item.get("primary_location") or {}
                results.append(record(item.get("display_name", ""), item.get("publication_date"),
                                      location.get("landing_page_url") or item.get("doi") or item["id"],
                                      abstract_from_index(item.get("abstract_inverted_index")), item.get("doi"), kind, quality))
            else:
                dates = (item.get("published") or {}).get("date-parts", [[]])[0]
                published = "-".join(str(n).zfill(2) if i else str(n) for i, n in enumerate(dates)) if len(dates) == 3 else None
                results.append(record((item.get("title") or [""])[0], published, item.get("URL", ""),
                                      item.get("abstract", ""), item.get("DOI"), kind, quality))
    return results
