import re
from .measurements import extract_measurements
from datetime import date
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def canonical_url(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(sorted(query)), ""))


def normalize_doi(doi):
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", (doi or "").strip().lower())


def process(records, config):
    # Union identifier aliases so cross-API bridge records cannot leave duplicates.
    parent = list(range(len(records)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    identifiers = {}
    for i, rec in enumerate(records):
        for key in (("doi", normalize_doi(rec["doi"])), ("url", canonical_url(rec["url"]))):
            if not key[1]:
                continue
            if key in identifiers:
                parent[root(i)] = root(identifiers[key])
            identifiers[key] = i
    groups = {}
    for i, rec in enumerate(records):
        groups.setdefault(root(i), []).append(rec)
    unique = []
    for group in groups.values():
        rec = max(group, key=lambda r: (r["source_quality"], len(r["text"])))
        doi, url = normalize_doi(rec["doi"]), canonical_url(rec["url"])
        rec = dict(rec, doi=doi or None, url=url)
        corpus = f"{rec['title']} {rec['text']}".casefold()
        matches = [k for k in config["keywords"] if k.casefold() in corpus]
        if not matches:
            continue
        published = None
        try:
            published = date.fromisoformat(rec["date"] or "")
        except ValueError:
            rec["date"] = None
        if config.get("date_from") or config.get("date_to"):
            if published is None:
                continue  # Unknown dates cannot satisfy an explicit date filter.
            if config.get("date_from") and published < date.fromisoformat(config["date_from"]):
                continue
            if config.get("date_to") and published > date.fromisoformat(config["date_to"]):
                continue
        recency = max(0, 1 - max(0, (date.today() - published).days) / 3650) if published else 0
        rec["keyword_matches"] = matches
        rec["score"] = round(0.65 * len(matches) / len(config["keywords"]) + 0.2 * recency + 0.15 * rec["source_quality"], 4)
        sentences = re.split(r"(?<=[.!?])\s+", rec["text"])
        excerpts = [s for s in sentences if any(k.casefold() in s.casefold() for k in matches)]
        rec["supporting_excerpt"] = " ".join(excerpts[:2])[:1000] or rec["title"]
        unique.append(extract_measurements(rec))
    return sorted(unique, key=lambda r: r["score"], reverse=True)
