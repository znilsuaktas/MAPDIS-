import json
from datetime import date
from urllib.parse import urlsplit


def load_config(path):
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")
    if not isinstance(config.get("sources"), list) or not config["sources"]:
        raise ValueError("sources must be a nonempty list")
    if not isinstance(config.get("keywords"), list) or not config["keywords"] or any(not isinstance(k, str) or not k.strip() for k in config["keywords"]):
        raise ValueError("keywords must be a nonempty list of strings")
    for key in ("date_from", "date_to"):
        if config.get(key):
            date.fromisoformat(config[key])
    if config.get("date_from") and config.get("date_to") and config["date_from"] > config["date_to"]:
        raise ValueError("date_from must precede date_to")
    if not 1 <= config.get("max_results_per_source", 10) <= 200:
        raise ValueError("max_results_per_source must be 1..200")
    if config.get("request_interval_seconds", 1) < 0.1:
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
