# Advanced workflow validation — 2026-10-16

Current implementation was tested in the cloud Linux environment. No Windows/PowerShell runtime is available here; the Windows scripts must be exercised on the user's computer.

Automated suite: **105 tests passed** (existing tests plus advanced workflow tests).

## Live API checks

- Oil profile, 2 queries × 2 pages × 2 API sources: 80 raw records, 37 retained after deduplication/topic/date filtering, 0 failed pages.
- Plastic profile, 1 query × 1 page × 2 API sources: 20 raw records, 9 retained, 0 failed pages.
- Mucilage profile, 1 query × 1 page × 2 API sources: 20 raw records, 10 retained, 0 failed pages.
- Offline replay of the oil run regenerated identical 37-record JSON, plus CSV/Markdown/HTML, without live discovery.
- CSV row counts, JSON lengths and HTML table row counts agreed.
- Validated release manifest hashes were unchanged.

These are academic discovery records, not newly verified pollution incidents. Counts are observations from this run, not guaranteed future yields. Some records lack abstracts; summaries do not invent missing content. The three samples are not one globally deduplicated dataset.

## Diagnosed API limitation

OpenAlex cursor page 2 initially returned HTTP 401 with `API key required for cursor paging`. The collector now uses its supported basic `page` parameter, which returned HTTP 200 for page 2 without credentials. The limit is capped at 20 pages × 200 records = 4000, below the basic-paging 10000-record ceiling. Crossref retains official cursor pagination. No authentication, TLS or anti-bot protection was bypassed.

## Local output paths (not published artifacts)

- `output/advanced_oil_basic_20261016/`
- `output/advanced_plastic_20261016/`
- `output/advanced_mucilage_20261016/`
- `output/advanced_replay_20261016/`

These runs are ignored by Git; source/configuration/tests and this validation note are versioned. Use the CLI to create new local runs. The pre-existing verified academic and incident release remains under `exports/mapdis_release/`.

## Broader pollution relevance update

The subsequent suite passed **127 tests**. A bounded sensor-independent literature run returned 15 records (all without Sentinel/SAR imagery keywords in title/abstract); a separate wastewater/chemical query run returned 17 records. These samples overlap and must not be summed as unique incidents. Both remain academic records, not automatically verified pollution events.

The BBC science/environment RSS endpoint and robots.txt eventually returned HTTP 200 after an initial proxy block. 42 actual feed entries were parsed, and zero met the marine-pollution contextual filter at that time. No successful pollution-news yield is claimed. The default RSS source remains disabled pending usage-terms review. Rule-based triage, false/uncertain statements, source separation and RSS/Atom handling are covered by tests; this does not establish universal semantic understanding or a measured real-world accuracy rate.
