import re
from .measurements import extract_measurements
from .matching import contains
from .context import assess
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
        assessment = assess(rec)
        rec["pollution_assessment"] = assessment
        if config.get("contextual_detection") and not assessment["marine_pollution_relevant"]:
            continue
        matches = [k for k in config["keywords"] if contains(corpus, k)]
        if any(contains(corpus, k) for k in config.get("exclude_keywords", [])):
            continue
        matched_groups = [name for name, terms in config.get("keyword_groups", {}).items() if any(contains(corpus, term) for term in terms)]
        if any(name not in matched_groups for name in config.get("required_keyword_groups", [])):
            continue
        rec["matched_groups"] = matched_groups
        rec["discovery"] = list({(d["source"], d["query"], d["page"]): d for r in group for d in r.get("discovery", [])}.values())
        rec["supporting_sources"] = list(dict.fromkeys(r["source"] for r in group))
        if not matches and not (config.get("contextual_detection") and assessment["marine_pollution_relevant"]):
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
        lexical = len(matches) / len(config["keywords"])
        if config.get("score_mode") == "grouped":
            lexical = min(1, max(len(matches), 1 if assessment["marine_pollution_relevant"] else 0) / config.get("relevance_match_target", 5))
        components = dict(relevance=round(0.65 * lexical, 4), recency=round(0.2 * recency, 4), quality=round(0.15 * rec["source_quality"], 4))
        rec["score_components"] = components
        rec["score"] = round(sum(components.values()), 4)
        sentences = re.split(r"(?<=[.!?])\s+", rec["text"])
        excerpts = [s for s in sentences if any(contains(s, k) for k in matches)]
        rec["supporting_excerpt"] = " ".join(excerpts[:2])[:1000] or rec["title"]
        unique.append(extract_measurements(rec))
    return sorted(unique, key=lambda r: r["score"], reverse=True)
