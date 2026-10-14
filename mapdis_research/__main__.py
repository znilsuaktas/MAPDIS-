import argparse
import logging
import sys
import json
import os
import requests
from pathlib import Path
from .notion import load_mapping, dry_run, read_schema
from .incidents import collect_incidents, write_incident_outputs
from .config import load_config
from .http import Client
from .sources import discover
from .processing import process
from .report import write_outputs, llm_analysis


def main(argv=None):
    parser = argparse.ArgumentParser(description="MAPDIS scientific and public-web research")
    parser.add_argument("command", choices=["run", "validate", "notion-export", "incidents"])
    parser.add_argument("--config", default="config/sample.json")
    parser.add_argument("--output", default="output")
    parser.add_argument("--llm", action="store_true", help="Send excerpts to configured LLM; output is an unverified draft")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--input", default="exports/mapdis_release/notion_events.json")
    parser.add_argument("--mapping", help="Confirmed 16-property mapping JSON")
    parser.add_argument("--notion-write", action="store_true", help="Disabled: Notion writes are prohibited in this workflow")
    parser.add_argument("--schema", help="Actual Notion schema JSON snapshot for option validation")
    parser.add_argument("--notion-read-schema", action="store_true", help="Read only the actual Notion database schema")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.notion_write:
            raise ValueError("Notion writes are disabled; explicit approval must be handled in a separate task")
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
        config = load_config(args.config)
        if args.command == "validate":
            logging.info("Configuration is valid")
            return 0
        records, statuses = [], []
        client = Client(config)
        for source in config.get("sources", []):
            if not source.get("enabled", True):
                statuses.append(dict(source=source["type"], status="disabled", count=0))
                continue
            try:
                found = discover(client, config, source)
                records.extend(found)
                statuses.append(dict(source=source["type"], status="success", count=len(found)))
            except Exception as exc:
                # Avoid logging exception URLs/headers which may contain authentication data.
                logging.error("Source %s failed (%s)", source["type"], type(exc).__name__)
                statuses.append(dict(source=source["type"], status="failed", error_type=type(exc).__name__))
        results = process(records, config)
        write_outputs(results, args.output, statuses)
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


if __name__ == "__main__":
    sys.exit(main())
