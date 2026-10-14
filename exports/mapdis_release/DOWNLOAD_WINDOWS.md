# Download and inspect MAPDIS exports on Windows

## What was actually verified

Files were opened in the cloud workspace, CSV parsing/encoding/headers/row counts were checked, and ZIP member integrity and SHA-256 checksums were verified. A browser download or chat attachment was **not** tested. This session has no callable file-upload, attachment or artifact-serving tool. The earlier internal workspace links were not download endpoints.

## Exact repository-relative paths

- `exports/mapdis_release/notion_import.csv` — five real incidents, exactly 16 confirmed columns.
- `exports/mapdis_release/notion_events.json` — structured incident records; unknown values are null.
- `exports/mapdis_release/research_evidence.json` — live retrieved sources, supporting quotes, original area evidence and timing disagreements.
- `exports/mapdis_release/research_report.md` — findings, citations and limitations.
- `exports/mapdis_release/notion_dry_run.json` — dry-run payloads, unknown-field lists, pending option validation.
- `exports/mapdis_release/validation.json` — incident counts and missing values by column.
- `exports/mapdis_release/academic_research.csv` — original 10-paper academic CSV, byte-for-byte preserved.
- `exports/mapdis_release/academic_original/` — original academic JSON/report/verification and raw responses.
- `exports/mapdis_release/original_csvs/` — copies of every previously generated CSV under `output/`, preserving their relative subdirectories.
- `exports/mapdis_release/csv_audit.json` — original and release CSV checks, including empty old outputs.
- `exports/mapdis_release/manifest.json` — file sizes and SHA-256 checksums.
- `exports/mapdis_release/MAPDIS_exports.zip` — all release files together.

The originals remain at `output/results.csv`, `output/live_sample/results.csv`, `output/sentinel1_verified/results.csv`, `output/sentinel1_measurements/results.csv`, and `output/sentinel1_measurements/notion_pages.json` (where present). Historical Notion previews use the superseded mapping and must not be imported into the confirmed incident database. Use only the new incident export for that database.

## Route A: Codex interface, if your product exposes file export

1. Open this task's workspace/file view, if the UI provides one.
2. Locate `exports/mapdis_release/MAPDIS_exports.zip`.
3. Use its file download/export action, if present.
4. If there is no file-export action, use Route B. An editor link alone is insufficient. Availability of this action and end-user downloads cannot be confirmed from the tools in this chat.

## Route B: GitHub branch, then Windows download

The exports are in a non-ignored folder but have **not been pushed**. First review the repository changes and publish them on a branch you approve. In the Codex workspace terminal, an authorized repository user can run:

```bash
cd /workspace/MAPDIS-
git status --short
git switch -c mapdis-incident-exports
git add README.md .env.example requirements.txt .gitignore config mapdis_research scripts tests exports/mapdis_release
git commit -m "Add confirmed incident exports and dry-run Notion mapping"
git push -u origin mapdis-incident-exports
```

Review the staged files before committing; never add `.env` or credentials. If the branch already exists, choose another branch name. Push permissions/authentication are required and were not tested; a GitHub read does not establish push access. These commands are instructions for the repository owner, not actions performed by this agent.

After a successful push:

1. On Windows, sign in to GitHub and open `znilsuaktas/MAPDIS-`.
2. Choose the pushed branch `mapdis-incident-exports` in the branch selector.
3. Navigate to `exports` → `mapdis_release` → `MAPDIS_exports.zip`.
4. Use **Download raw file** / the download icon for that file. Save it in your Downloads folder.
5. In File Explorer, right-click the ZIP → **Extract All**.
6. Open `research_report.md` and `notion_events.json` in VS Code or a text editor.
7. Inspect CSV in Excel through **Data → From Text/CSV**, select **UTF-8** and comma delimiter. Keep Estimated Area as text. Both files include a UTF-8 BOM.

To download CSVs individually, repeat steps 3–4 for `notion_import.csv` and `academic_research.csv`. Do not click GitHub's CSV rendered table and save the webpage as CSV.

Alternatively, once the branch exists remotely, use Git for Windows:

```powershell
cd $env:USERPROFILE\Downloads
git clone --branch mapdis-incident-exports https://github.com/znilsuaktas/MAPDIS-.git MAPDIS-export
cd MAPDIS-export\exports\mapdis_release
```

This is a documented GitHub retrieval route, not a verified browser download from this task. It requires an actual successful push first.

## Verify downloaded contents in PowerShell

In the extracted folder, verify all manifest files:

```powershell
$manifest = Get-Content .\manifest.json -Raw | ConvertFrom-Json
foreach ($entry in $manifest.PSObject.Properties) {
    $actual = (Get-FileHash -LiteralPath $entry.Name -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.Value.sha256) { throw "Checksum mismatch: $($entry.Name)" }
}
$events = @(Import-Csv -LiteralPath .\notion_import.csv -Encoding UTF8)
$papers = @(Import-Csv -LiteralPath .\academic_research.csv -Encoding UTF8)
"Incident rows: $($events.Count)"
"Incident columns: $($events[0].PSObject.Properties.Count)"
"Academic rows: $($papers.Count)"
```

Expected: 5 incident rows, 16 incident columns, 10 academic rows. Empty cells mean unknown, not false. The JSON is authoritative for unknown booleans and date-range structure.

Do not import into Notion yet: actual Select/Multi-select options are unverified; CSV checkbox blanks can become false, and ISO date-range CSV parsing has not been tested. No Notion write is authorized or performed by this workflow.
