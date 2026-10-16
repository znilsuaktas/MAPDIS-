# MAPDIS-AI Research Agent

A modular Python 3.10+ MVP for scientific literature, news, and public incident records about marine pollution and satellite detection. Uses OpenAlex/Crossref metadata APIs and explicitly approved public HTML sources. No API key or LLM is required for extractive research.

## Advanced local workflow

Türkçe adım adım kurulum ve hoca sunumu: [docs/LOCAL_DEMO_TR.md](docs/LOCAL_DEMO_TR.md).

The original sample workflow is preserved. `config/advanced.json` adds 89 distinct Turkish/English matching phrases across four profiles (`oil_spill`, `plastic`, `mucilage`, `all`), bounded API pagination (OpenAlex basic pages; Crossref cursors), explicit query planning, required topic groups, exclusions, provenance-preserving deduplication, richer metadata, an offline searchable HTML dashboard, and offline replay.

```powershell
.\.venv\Scripts\python.exe -m mapdis_research profiles
.\.venv\Scripts\python.exe -m mapdis_research plan --profile oil_spill --max-queries 2 --pages 2
.\.venv\Scripts\python.exe -m mapdis_research run --profile oil_spill --max-queries 2 --pages 2
```

Without `--output`, commands choose a timestamped directory. An existing nonempty output directory is rejected, protecting reviewed exports. `summary.json`, `search_log.json`, `raw_records.json`, and `effective_config.json` accompany each research run. `dashboard.html` opens directly in a browser with no local server. Replay an existing run without API calls:

```powershell
.\.venv\Scripts\python.exe -m mapdis_research replay --input output/YOUR_RUN/raw_records.json --config output/YOUR_RUN/effective_config.json
```

`queries` limits API discovery requests; `keywords` is a separate local matching dictionary. `max_results_per_source` is the page size per query, and `pages_per_query` bounds API pages. Both API 401/403/429 and transport failures stop that source without aggressive retries; partial results remain, and live runs return exit 1 when a page fails. Required keyword groups must all match. Source quality is a heuristic; topic matches do not verify real-world incidents. The original sample keeps its legacy score, while advanced profiles use bounded phrase-count saturation so adding synonyms does not dilute every result.

The `.ps1` helpers (`Setup-Local.ps1`, `Run-Local.ps1`) and VS Code F5 configuration simplify local use. Direct Python commands remain available if script execution policy blocks the helpers. Windows execution itself is not tested by Linux cloud validation.

## Windows setup and VS Code demonstration (PowerShell)

Install Git for Windows, Python 3.10 or newer (with the Python launcher), and VS Code with Microsoft's Python extension. Open PowerShell and run:

```powershell
cd $env:USERPROFILE\Documents
git clone --branch feature/mapdis-scraper https://github.com/znilsuaktas/MAPDIS-.git
cd MAPDIS-
code .
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m mapdis_research validate --config config/sample.json
```

If you already cloned the repository, use `git fetch origin` then `git switch feature/mapdis-scraper` instead of cloning again. In VS Code choose **Python: Select Interpreter** and select `.venv\Scripts\python.exe`. Use the integrated terminal with PowerShell. Direct interpreter invocation avoids activation-policy changes.

The exact CLI entry-point file is **`mapdis_research/__main__.py`**, with `main()` called by `python -m mapdis_research`. Do not invoke it as a standalone script because its imports are package-relative.

For your professor, demonstrate a new search and new CSV generation:

```powershell
$demoOutput = "output/demo_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff")
.\.venv\Scripts\python.exe -m mapdis_research run --config config/sample.json --output $demoOutput
Get-Content "$demoOutput/run.json"
$paperRows = @(Import-Csv "$demoOutput/results.csv" -Encoding UTF8)
"Paper rows generated: $($paperRows.Count)"
```

Each execution chooses a new directory to preserve validated exports. Outputs include `results.csv`, `results.json`, `report.md`, and source statuses in `run.json`. Open the CSV in Excel via **Data → From Text/CSV**, UTF-8 and comma delimiter, or view it in VS Code. Exit 1/source failures mean the dataset may be partial; do not describe an empty output as a successful research run.

To change search keywords without replacing the sample configuration:

```powershell
Copy-Item config/sample.json config/my_search.json
code config/my_search.json
```

Edit the keyword/date/source settings, then run with `--config config/my_search.json` and a new `$demoOutput` directory. API Internet access is required. Extractive searches need no API keys or LLM credentials.

Incident collection is a separate demonstration using reviewed facts and live source lookups:

```powershell
$incidentOutput = "output/incidents_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff")
.\.venv\Scripts\python.exe -m mapdis_research incidents --config config/incidents.json --output $incidentOutput
$incidentRows = @(Import-Csv "$incidentOutput/notion_import.csv" -Encoding UTF8)
"Incident rows: $($incidentRows.Count)"
"Incident columns: $($incidentRows[0].PSObject.Properties.Count)"
```

The research demo performs API discovery; the incident demo refreshes sources and verifies a curated extraction manifest. It does not automatically turn every paper into an incident. Existing reviewed artifacts stay under `exports/mapdis_release/` and are not overwritten by these commands. Do not run `scripts/package_outputs.py` against the reviewed release unless you explicitly intend to refresh that release bundle.

On Linux/macOS use `python3 -m venv .venv` and `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`. Automated tests are mocked/offline; live access was tested separately in the cloud, not on a Windows computer.

## Configure research

Edit `config/sample.json` or copy it to another JSON file. Keywords are case-insensitive literal phrases. `date_from` and `date_to` are inclusive ISO dates; null disables a bound. Unknown dates are excluded when any date bound is active. API date filters reduce discovery results; the same bounds are applied locally. Crossref dates with only a year/month remain unknown rather than inventing a day.

Each enabled API source queries each keyword, up to `max_results_per_source` records **per keyword** (1–200). Public websites fetch at most this many pages per source, starting with the configured URL and same-origin links on that page. This MVP is bounded discovery, not an exhaustive crawler. JavaScript-only sites and PDFs are not parsed. Add public news or incident sources as follows only after reviewing their terms:

```json
{"type": "website", "url": "https://your-permitted-public-source.example/incidents", "enabled": true, "terms_reviewed": true, "quality": 0.7}
```

Replace the placeholder with a real permitted source. The sample website is intentionally disabled. `terms_reviewed` records your review; robots permission alone does not grant legal permission. Websites require robots permission, and ambiguous/unavailable robots policies fail closed. HTTP 404 robots policies mean no declared restrictions. Requests use HTTPS verification, timeouts, a user agent, pacing, crawl-delay/request-rate, and conservative redirects. HTTP 429/403 and other failures are reported without evasion or automatic aggressive retries. Do not enable sources whose terms prohibit automated collection; do not supply private/login/paywalled URLs. The agent skips explicit password forms but cannot reliably detect every paywall or anti-bot page; use curated public sources and review extracted text. API discovery follows official API access rather than scraping API landing pages.

Quality weights are configurable heuristics, not fact verification. Ranking uses keyword coverage (65%), date recency over ten years (20%), and source quality (15%). DOI and canonical URL remove duplicate records; the richer/high-quality representation is retained, and alternative duplicate metadata is not merged. Supporting excerpts come only from retrieved text or titles, never fabricated abstracts.

## Outputs and exit codes

- `results.json`: records with titles, publication dates, DOI, source URLs, retrieved text, keyword matches, scores, and supporting excerpts.
- `results.csv`: the same data, UTF-8 BOM for Excel; formula-like strings are prefixed with an apostrophe.
- `report.md`: cited extractive evidence, explicit uncertainty, disagreements requiring review, and missing information.
- `run.json`: source successes, failures, disabled sources, and raw counts.

Exit 0 means enabled sources completed, not that real-world facts were independently verified or that results exist. Exit 1 means a source or optional LLM failed; partial extractive outputs are retained. Exit 2 means invalid configuration/setup. Use `--verbose` for extra logging. No result should be treated as a verified incident solely because an article mentions it. Disagreement detection is deliberately left to evidence review in this MVP; the report never invents conflicts or asserts consensus.

## Optional LLM

`.env.example` documents variables; `.env` is **not automatically loaded**. Export values securely, never commit credentials. PowerShell example:

```powershell
$env:LLM_API_KEY = "your-key"
$env:LLM_MODEL = "gpt-4o-mini"
.\.venv\Scripts\python.exe -m mapdis_research run --llm
```

`LLM_API_URL` optionally selects an OpenAI-compatible HTTPS chat-completions endpoint. `--llm` sends at most 30 source excerpts to that provider, so use it only with data you are allowed to share. Model output is saved separately as `llm_analysis_unverified.md`, requires human citation/fact checking, and is never presented as verified findings. Without `--llm`, there is no LLM request or credential requirement.

## Structure and tests

`config.py` validates JSON, `http.py` handles transport/robots, `sources.py` implements source adapters, `processing.py` filters/deduplicates/ranks, `report.py` writes outputs and optional analysis, and `__main__.py` provides the CLI. Add source adapters through `discover` and config validation. Tests use local fixtures/mocks and do not need Internet or paid APIs.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mapdis_research validate
.venv/bin/python -m mapdis_research run
```

## Incident collection and confirmed Notion mapping

Academic search remains `run --config config/sample.json`. Pollution incidents use a separate evidence-reviewed configuration and output pipeline:

```powershell
.\.venv\Scripts\python.exe -m mapdis_research incidents --config config/incidents.json --output output/incidents_new
.\.venv\Scripts\python.exe -m mapdis_research notion-export --input exports/mapdis_release/notion_events.json --mapping config/notion_mapping.json --output output/notion_incident_preview
.\.venv\Scripts\python.exe -m pytest -q
```

On Linux use `.venv/bin/python`. The incident collector retrieves publications by configured DOI from OpenAlex, checks DOI/title identity against Crossref, verifies that each configured supporting quote actually appears in the retrieved title/abstract, and exports reviewed incident facts. `config/incidents.json` is a transparent curated extraction manifest, not an automatic inference from arbitrary papers. Adding a new incident requires reviewing sources, populating only supported facts, and assigning a stable event ID. A publication's release date is never substituted for an incident date. Repeated identical event IDs are deduplicated; conflicting records need review. Separate incident IDs are retained when one publication covers multiple events.

| Order | Property | Notion type |
|---|---|---|
| 1 | Event Name | Title |
| 2 | Pollution Type | Select |
| 3 | Event Date | Date |
| 4 | Satellite Observation Date | Date |
| 5 | Country | Rich Text |
| 6 | Sea / Region | Rich Text |
| 7 | Cause | Select |
| 8 | Estimated Area | Rich Text |
| 9 | Image Type | Multi-select |
| 10 | Source | URL |
| 11 | Useful for Classifier | Select |
| 12 | Notes | Rich Text |
| 13 | Satellite Image Available | Checkbox |
| 14 | Bounding Box Possible | Checkbox |
| 15 | Source Type | Select |
| 16 | Status | Select |

These exact names, order and types replace the provisional mapping. Longitude is **not** mapped to Notion because its database name/type are unconfirmed. Source-only longitude extraction and numeric km² enrichment remain available in the academic pipeline; they do not change Estimated Area's confirmed Rich Text type. Existing academic fields and outputs remain intact. Legacy ten-property preview code is retained for compatibility, but its writes are disabled. New academic runs write `academic_notion_preview.json`, clearly distinct from incident exports.

`notion_import.csv` has exactly the 16 confirmed headers, UTF-8 BOM for Windows/Excel, and quoted fields. Estimated Area preserves original text and units. JSON includes `area_evidence` with the original value/unit, derived km² when applicable, source and uncertainty. Volume/mass are never area. Date fields are null or ISO 8601 `start`/`end` objects; CSV date ranges use ISO intervals such as `2021-03-10/2021-06-06`. This preserves observation intervals but does not claim daily observations. Notion API previews retain both start/end; native Notion CSV date-range parsing has not been tested and may require manual handling.

Unknowns are null in research JSON and blank in CSV. Unknown Notion checkboxes are omitted from payload previews rather than converted to false. **Native Notion CSV import can coerce blank checkbox cells to unchecked**, so CSV cannot preserve three-valued checkbox semantics inside Notion by itself. Keep `notion_events.json`/evidence authoritative and review this limitation before any manual import. `Satellite Image Available=true` requires an identified verified image asset with supporting evidence; published analysis of satellite images alone is only `imagery_documented=true`. Bounding Box Possible requires verified bounds and evidence. Classifier candidates denote potential review value, not verified training datasets or a confirmed Notion Select option.

## Schema validation and write protection

All Notion synchronization is dry-run only. `--notion-write` returns an error before any Notion operation; both legacy and current exporter write methods refuse execution. No existing Notion records, schemas or pages are touched. An approved future synchronization task must explicitly implement/enable its approved scope.

Confirmed property types are not enough to validate option names. To check actual options, supply a **real database schema snapshot**, not a fabricated/example schema:

```powershell
.\.venv\Scripts\python.exe -m mapdis_research notion-export --input exports/mapdis_release/notion_events.json --schema actual_notion_schema.json --output output/notion_checked
```

Alternatively export `NOTION_TOKEN` and `NOTION_DATABASE_ID` securely and use `--notion-read-schema`, which makes only a GET request to Notion API version `2022-06-28`. Cloud access to `api.notion.com` may need an environment permission. No credentials are required for offline previews. Without an actual schema, validation remains `pending` and semantic labels such as Oil spill/SAR are explicitly unconfirmed options; do not import/synchronize yet. The adapter compares every Select/Multi-select value to the provided schema options and checks all 16 types. Longitude is excluded even if an unrelated schema property exists.

## Final files and download limitations

See `exports/mapdis_release/DOWNLOAD_WINDOWS.md` for exact repository-relative paths and Windows retrieval steps. The release contains the incident CSV/JSON/evidence/report, the separately preserved original academic CSV, a CSV audit, validation report, checksums, and a ZIP. Existing `output/` data is preserved; the release directory is not ignored by Git.

This Codex session exposes shell access but no attachment, artifact-upload or file-serving API. Internal `/workspace/...` Markdown links navigate workspace files and are not verified download endpoints. ZIP readability and checksums can be tested locally; that does not test a browser download. Files must be transferred using an available Codex UI file-export action (if your UI provides one), or committed/pushed to an approved GitHub branch and then downloaded. Notion writes remain disabled. Use the `feature/mapdis-scraper` branch for this review; any older export-folder download instructions naming another branch are historical snapshot instructions.

## Notion schema status for review

The user-confirmed **Estimated Area** property remains **Rich Text**, with its original unit preserved in incident CSV/JSON. It is not converted into a Notion Number property. The exact Notion name/type for **Longitude** is still unconfirmed, so it remains unmapped; longitude extraction and source evidence remain available in research JSON. No confirmed Longitude property has been deleted. The actual live Notion schema cannot be checked without configured `NOTION_TOKEN` and `NOTION_DATABASE_ID` or an authentic schema snapshot. Select/Multi-select options therefore remain pending. No Notion record or schema is written by the demo.

## Download the reviewed exports from GitHub

After the branch is pushed, select `feature/mapdis-scraper` on GitHub, open `exports/mapdis_release/MAPDIS_exports.zip`, and use **Download raw file**. Alternatively use **Code → Download ZIP** while viewing that branch to retrieve source and exports together, then extract it in Windows. Individual incident and academic CSVs are `exports/mapdis_release/notion_import.csv` and `exports/mapdis_release/academic_research.csv`. Their integrity and ZIP contents were checked locally; browser download behavior was not tested by the agent.
