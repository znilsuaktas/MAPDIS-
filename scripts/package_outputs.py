"""Audit every workspace CSV, preserve originals, and build a local ZIP.

This script does not upload anything or assert that UI downloading works.
"""
import csv
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'exports/mapdis_release'


def audit_csv(path):
    data = path.read_bytes()
    text = data.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(text, newline=''), strict=True))
    if not rows or not rows[0] or any(not h for h in rows[0]) or len(set(rows[0])) != len(rows[0]):
        raise ValueError(f'Missing/duplicate CSV headers: {path}')
    headers, records = rows[0], rows[1:]
    if any(len(row) != len(headers) for row in records):
        raise ValueError(f'Inconsistent CSV column count: {path}')
    key = 'doi' if 'doi' in headers else 'Event Name' if 'Event Name' in headers else None
    identities = [row[headers.index(key)].casefold() for row in records if row[headers.index(key)]] if key else []
    return {'path': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            'readable': True, 'encoding': 'UTF-8 with BOM' if data.startswith(b'\xef\xbb\xbf') else 'UTF-8',
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'rows': len(records), 'columns': len(headers), 'headers': headers,
            'identical_duplicate_rows': len(records)-len(set(map(tuple,records))),
            'duplicate_identity_count': len(identities)-len(set(identities)),
            'identity_column': key,
            'missing_values': {name: sum(row[i] == '' for row in records) for i,name in enumerate(headers)}}


def main():
    RELEASE.mkdir(parents=True,exist_ok=True)
    # Include all CSV files currently present, not only the final 16-column output.
    found = sorted(Path('/workspace').rglob('*.csv'))
    audits = [audit_csv(p) for p in found]
    for path in found:
        if path.is_relative_to(ROOT / 'output'):
            destination = RELEASE / 'original_csvs' / path.relative_to(ROOT / 'output')
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,destination)
    academic = ROOT / 'output/sentinel1_verified/results.csv'
    if not academic.exists():
        raise FileNotFoundError('The original citation-verified academic CSV is missing')
    shutil.copyfile(academic, RELEASE / 'academic_research.csv')
    if academic.read_bytes() != (RELEASE/'academic_research.csv').read_bytes():
        raise ValueError('Academic CSV copy mismatch')
    # Preserve the academic evidence/report separately from pollution events.
    shutil.copytree(ROOT/'output/sentinel1_verified', RELEASE/'academic_original', dirs_exist_ok=True)
    (RELEASE/'csv_audit.json').write_text(json.dumps({'workspace_csvs':audits,'release_csvs':[audit_csv(p) for p in sorted(RELEASE.rglob('*.csv'))]},indent=2)+'\n',encoding='utf-8')
    files=[p for p in sorted(RELEASE.rglob('*')) if p.is_file() and p.name not in {'MAPDIS_exports.zip','manifest.json'}]
    manifest={str(p.relative_to(RELEASE)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
    (RELEASE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive = RELEASE/'MAPDIS_exports.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files+[RELEASE/'manifest.json']:
            z.write(p,p.relative_to(RELEASE))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Corrupt ZIP member')
        for name,details in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=details['sha256']:
                raise ValueError('ZIP checksum mismatch')
    print(f'CSV files audited: {len(found)}; release CSV files: {len(list(RELEASE.rglob("*.csv")))}. ZIP integrity and member checksums verified locally.')
    print('No attachment/upload capability is available; no download was tested.')


if __name__ == '__main__':
    main()
