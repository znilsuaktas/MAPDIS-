import argparse
import logging
import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from .notion import load_mapping, dry_run, read_schema
from .incidents import collect_incidents, write_incident_outputs
from .config import load_config
from .http import Client
from .sources import discover
from .processing import process
from .report import write_outputs, llm_analysis


def main(argv=None):
    parser = argparse.ArgumentParser(description="MAPDIS scientific and public-web research")
    parser.add_argument("command", choices=["run", "validate", "notion-export", "incidents", "profiles", "plan", "replay", "news-pilot", "review-pilot"])
    parser.add_argument("--config", default="config/sample.json")
    parser.add_argument("--output", help="New output directory; default is timestamped")
    parser.add_argument("--llm", action="store_true", help="Send excerpts to configured LLM; output is an unverified draft")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--input", default="exports/mapdis_release/notion_events.json")
    parser.add_argument("--mapping", help="Confirmed 16-property mapping JSON")
    parser.add_argument("--notion-write", action="store_true", help="Disabled: Notion writes are prohibited in this workflow")
    parser.add_argument("--schema", help="Actual Notion schema JSON snapshot for option validation")
    parser.add_argument("--notion-read-schema", action="store_true", help="Read only the actual Notion database schema")
    parser.add_argument("--profile", help="marine_pollution, oil_spill, plastic, mucilage, or all (advanced config)")
    parser.add_argument("--max-queries", type=int, help="Bound API queries per source (1..100)")
    parser.add_argument("--pages", type=int, help="Bound pages per query (1..20)")
    parser.add_argument("--provider", choices=["gdelt", "rss"], help="Independent news source; does not bypass provider limits")
    args = parser.parse_args(argv)
    if args.output is None:
        args.output = str(Path("output") / datetime.now().strftime("run_%Y%m%d_%H%M%S_%f"))
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.notion_write:
            raise ValueError("Notion writes are disabled; explicit approval must be handled in a separate task")
        if args.command in {"run", "replay", "incidents", "notion-export", "news-pilot"}:
            target = Path(args.output)
            if target.exists() and (not target.is_dir() or any(target.iterdir())):
                logging.error("Choose a new or empty --output directory; previous results were preserved")
                raise ValueError("Output directory must be new or empty; validated files are never overwritten")
        if args.command == "news-pilot":
            from .pilot import load_pilot_config, collect_news, write_pilot
            config = load_pilot_config(("config/news_rss_pilot.json" if args.provider == "rss" else "config/news_pilot.json") if args.config == "config/sample.json" else args.config)
            if args.provider and config.get("provider", "gdelt") != args.provider:
                raise ValueError("Selected provider must match its configuration")
            raw, statuses = collect_news(config)
            summary = write_pilot(raw, statuses, config, args.output)
            logging.info("News pilot: %d/%d records. Output: %s", summary["sample_count"], summary["target"], args.output)
            if not summary["sample_count"]:
                logging.error("No news collected; quality review cannot start. Inspect %s/collection_status.json", args.output)
            else:
                logging.info("Manual review required: %s/quality_review.csv", args.output)
            return 1 if summary["shortfall"] or any(s["status"] == "failed" for s in statuses) else 0
        if args.command == "review-pilot":
            from .pilot import evaluate_reviews
            print(json.dumps(evaluate_reviews(args.input), ensure_ascii=False, indent=2))
            return 0
        schema = json.loads(Path(args.schema).read_text(encoding="utf-8")) if args.schema else None
        if args.notion_read_schema:
            schema = read_schema()
        if args.command == "incidents":
            events, sources = collect_incidents("config/incidents.json" if args.config == "config/sample.json" else args.config)
            stats = write_incident_outputs(events, sources, args.output, schema)
            logging.info("Collected %d real incidents; imagery assets confirmed: %d", stats["incidents"], stats["satellite_images_confirmed_available"])
            return 0
        if args.command == "notion-export":
            load_mapping(args.mapping)
            records = json.loads(Path(args.input).read_text(encoding="utf-8"))
            plan = dry_run(records, schema)
            path = Path(args.output)
            path.mkdir(parents=True, exist_ok=True)
            (path / "notion_dry_run.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            logging.info("Notion dry-run only; option validation: %s", plan["schema_validation"]["status"])
            return 0
        config_path = args.config
        if (args.profile or args.command in {"profiles", "plan"}) and config_path == "config/sample.json":
            config_path = "config/advanced.json"
        config = load_config(config_path, args.profile)
        for arg, key, bound in ((args.max_queries, "max_queries", 100), (args.pages, "pages_per_query", 20)):
            if arg is not None:
                if not 1 <= arg <= bound:
                    raise ValueError(key + " outside its allowed bounds")
                config[key] = arg
        if args.command == "profiles":
            for name, profile in config.get("profiles", {}).items():
                print(f"{name}: {profile.get('description', '')} ({len(profile['keywords'])} phrases)")
            return 0
        if args.command == "plan":
            queries = config.get("queries", config["keywords"])[:config.get("max_queries", 100)]
            api_sources = sum(s.get("enabled", True) and s["type"] in {"openalex", "crossref"} for s in config["sources"])
            calls = len(queries) * config.get("pages_per_query", 1) * api_sources
            print(json.dumps({"profile": config.get("selected_profile"), "keywords": len(config["keywords"]), "queries": queries,
                "max_api_requests": calls, "max_raw_api_records": calls * config.get("max_results_per_source", 10),
                "note": "Upper bound, not guaranteed yield; public websites have separate page limits"}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "replay":
            records = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(records, list):
                raise ValueError("Replay input must be a raw record list")
            results = process(records, config)
            write_outputs(results, args.output, [{"source": "offline_replay", "status": "success", "count": len(records)}])
            save_run_details(args.output, config, records, results, [], replay=True)
            logging.info("Offline replay saved %d records to %s", len(results), args.output)
            return 0
        if args.command == "validate":
            logging.info("Configuration is valid")
            return 0
        records, statuses = [], []
        client = Client(config)
        client.diagnostics = []
        for source in config.get("sources", []):
            if not source.get("enabled", True):
                statuses.append(dict(source=source["type"], status="disabled", count=0))
                continue
            try:
                found = discover(client, config, source)
                records.extend(found)
                failed = any(d["status"] == "failed" and d["source"] == source["type"] for d in client.diagnostics)
                statuses.append(dict(source=source["type"], status="failed" if failed else "success", count=len(found)))
            except Exception as exc:
                # Avoid logging exception URLs/headers which may contain authentication data.
                logging.error("Source %s failed (%s)", source["type"], type(exc).__name__)
                statuses.append(dict(source=source["type"], status="failed", error_type=type(exc).__name__))
        results = process(records, config)
        write_outputs(results, args.output, statuses)
        save_run_details(args.output, config, records, results, client.diagnostics)
        if args.llm:
            try:
                analysis = llm_analysis(results)
                write_outputs(results, args.output, statuses, analysis)
            except Exception as exc:
                logging.error("LLM failed (%s); extractive outputs retained", type(exc).__name__)
                return 1
        logging.info("Saved %d records to %s", len(results), args.output)
        return 1 if any(s["status"] == "failed" for s in statuses) else 0
    except (ValueError, KeyError, TypeError, OSError, requests.RequestException) as exc:
        logging.error("Setup/configuration error (%s)", type(exc).__name__)
        return 2


def save_run_details(output, config, records, results, diagnostics, replay=False):
    path = Path(output)
    path.mkdir(parents=True, exist_ok=True)
    # Public research inputs only; credentials are never read from configuration.
    allowed = {"keywords", "queries", "exclude_keywords", "keyword_groups", "required_keyword_groups", "selected_profile",
               "date_from", "date_to", "max_results_per_source", "request_interval_seconds", "user_agent", "sources",
               "pages_per_query", "max_queries", "score_mode", "relevance_match_target", "contextual_detection"}
    snapshot = {k: v for k, v in config.items() if k in allowed}
    for filename, data in (("raw_records.json", records), ("effective_config.json", snapshot), ("search_log.json", diagnostics)):
        (path / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = dict(profile=config.get("selected_profile"), finished_at_utc=datetime.now(timezone.utc).isoformat(),
                   mode="offline_replay" if replay else "live", raw_records=len(records), returned_records=len(results),
                   removed_by_dedup_or_filters=len(records)-len(results),
                   records_without_abstract=sum(not r["text"] for r in results),
                   records_by_source=dict(Counter(r["source"] for r in results)),
                   records_by_group=dict(Counter(g for r in results for g in r.get("matched_groups", []))),
                   records_by_kind=dict(Counter(r.get("pollution_assessment", {}).get("record_kind", "unknown") for r in results)),
                   failed_pages=sum(d["status"] == "failed" for d in diagnostics))
    (path / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
