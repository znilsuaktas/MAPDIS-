import json
import math
from datetime import date
from urllib.parse import urlsplit


def load_config(path, profile=None):
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")
    profiles = config.get("profiles", {})
    selected = profile or config.get("default_profile")
    if selected:
        if selected not in profiles:
            raise ValueError("Unknown search profile: " + selected)
        config.update(profiles[selected])
        config["selected_profile"] = selected
    for key in ("keywords", "queries", "exclude_keywords"):
        if key in config:
            values = config[key]
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError(key + " must contain nonblank strings")
            config[key] = list(dict.fromkeys(v.strip() for v in values))
    if "queries" in config and not config["queries"]:
        raise ValueError("queries cannot be empty")
    for key, default, maximum in (("pages_per_query", 1, 20), ("max_queries", 100, 100)):
        value = config.get(key, default)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(key + " is outside its allowed bounds")
    groups = config.get("keyword_groups", {})
    if not isinstance(groups, dict) or any(not isinstance(terms, list) or not terms or any(not isinstance(t, str) or not t.strip() for t in terms) for terms in groups.values()):
        raise ValueError("keyword_groups must map group names to nonempty phrase lists")
    required = config.get("required_keyword_groups", [])
    if not isinstance(required, list) or any(g not in groups for g in required):
        raise ValueError("required_keyword_groups contains an unknown group")
    if config.get("score_mode", "legacy") not in {"legacy", "grouped"}:
        raise ValueError("unknown score_mode")
    if type(config.get("relevance_match_target", 5)) is not int or config.get("relevance_match_target", 5) < 1:
        raise ValueError("relevance_match_target must be a positive integer")
    if not isinstance(config.get("sources"), list) or not config["sources"]:
        raise ValueError("sources must be a nonempty list")
    if not isinstance(config.get("keywords"), list) or not config["keywords"] or any(not isinstance(k, str) or not k.strip() for k in config["keywords"]):
        raise ValueError("keywords must be a nonempty list of strings")
    for key in ("date_from", "date_to"):
        if config.get(key):
            date.fromisoformat(config[key])
    if config.get("date_from") and config.get("date_to") and config["date_from"] > config["date_to"]:
        raise ValueError("date_from must precede date_to")
    if type(config.get("max_results_per_source", 10)) is not int or not 1 <= config.get("max_results_per_source", 10) <= 200:
        raise ValueError("max_results_per_source must be 1..200")
    if type(config.get("request_interval_seconds", 1)) not in (int, float) or not math.isfinite(config.get("request_interval_seconds", 1)) or config.get("request_interval_seconds", 1) < 0.1:
        raise ValueError("request interval must be at least 0.1 seconds")
    for source in config.get("sources", []):
        if not isinstance(source, dict):
            raise ValueError("each source must be an object")
        if source["type"] not in {"openalex", "crossref", "website"}:
            raise ValueError("unsupported source type")
        if not 0 <= source.get("quality", 0.5) <= 1:
            raise ValueError("source quality must be 0..1")
        if source["type"] == "website" and urlsplit(source.get("url", "")).scheme != "https":
            raise ValueError("websites must use HTTPS")
    return config
