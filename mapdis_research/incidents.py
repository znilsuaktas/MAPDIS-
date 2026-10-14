"""Evidence-reviewed incident records, separate from academic search results."""
import csv
import difflib
import re
import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from .http import Client
from .sources import abstract_from_index
from .notion import SCHEMA, dry_run
from .processing import normalize_doi


def validate_date(value):
    if value is None:
        return
    if not isinstance(value, dict) or not set(value) <= {'start', 'end'} or not value.get('start'):
        raise ValueError('Dates must be null or ISO 8601 start/end objects')
    start = date.fromisoformat(value['start'])
    if value.get('end') and date.fromisoformat(value['end']) < start:
        raise ValueError('Date range ends before its start')


def validate_event(event):
    if event.get('record_kind') != 'pollution_incident' or not event.get('event_id') or not event.get('event_name'):
        raise ValueError('An explicitly identified pollution incident is required, not paper metadata')
    validate_date(event.get('event_date'))
    validate_date(event.get('satellite_observation_date'))
    for field in ('satellite_image_available', 'bounding_box_possible', 'classifier_candidate'):
        if event.get(field) is not None and type(event[field]) is not bool:
            raise ValueError(f'{field} must be true, false, or null')
    for _, (field, kind) in SCHEMA.items():
        value = event.get(field)
        if kind in {'title', 'rich_text', 'select', 'url'} and value is not None and not isinstance(value, str):
            raise ValueError(f'{field} must be text or null')
        if kind == 'multi_select' and value is not None and (not isinstance(value, list) or not all(isinstance(v, str) for v in value)):
            raise ValueError('image_type must be a list of strings or null')
    if urlsplit(event.get('source_url') or '').scheme != 'https':
        raise ValueError('An HTTPS citation is required')
    evidence = event.get('field_evidence', {})
    for field in ('satellite_image_available', 'bounding_box_possible', 'classifier_candidate'):
        if event.get(field) is not None and not evidence.get(field):
            raise ValueError(f'{field} requires supporting evidence even when false')
    if event.get('satellite_image_available') is True and not event.get('imagery_assets'):
        raise ValueError('Available imagery requires an identified verified imagery asset')
    if event.get('bounding_box_possible') is True:
        box = event.get('bounding_box')
        if not isinstance(box, list) or len(box) != 4 or not all(type(v) in (int, float) for v in box):
            raise ValueError('A verified bounding box is required')
        west,south,east,north = box
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError('Bounding box outside geographic bounds')
    if event.get('longitude') is not None:
        from .measurements import validate_measurements
        validate_measurements(event)
    area = event.get('estimated_area')
    if area and any(unit in area.casefold() for unit in ('ton', 'barrel', 'litre', 'liter', 'm³', 'm3')):
        raise ValueError('Volume or mass cannot be Estimated Area')
    # Every populated event fact must cite a retrieved source; workflow labels are separate.
    for field in ('event_name', 'pollution_type', 'event_date', 'satellite_observation_date', 'country', 'sea_region', 'cause', 'estimated_area', 'image_type'):
        if event.get(field) is not None and not evidence.get(field):
            raise ValueError(f'{field} has no source evidence')


def deduplicate_events(events):
    # Never deduplicate different incidents just because the same paper covers them.
    groups = {}
    for event in events:
        validate_event(event)
        identity = event['event_id']
        if identity not in groups:
            groups[identity] = event
        elif groups[identity] != event:
            raise ValueError(f'Conflicting evidence for incident {identity}; review before merging')
    return list(groups.values())


def collect_incidents(config_path):
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    client = Client(config)
    sources = {}
    for item in config['sources']:
        doi = normalize_doi(item['doi'])
        endpoint = 'https://api.openalex.org/works/https://doi.org/' + quote(doi, safe='/')
        response = client.get(endpoint)
        work = response.json()
        if normalize_doi(work.get('doi')) != doi or work.get('is_retracted'):
            raise ValueError('Source DOI mismatch or retracted publication')
        crossref_url = 'https://api.crossref.org/works/' + quote(doi, safe='')
        cr = client.get(crossref_url).json()['message']
        normalized = lambda text: re.sub(r'[^a-z0-9]', '', text.lower())
        similarity = difflib.SequenceMatcher(None, normalized(work['display_name']), normalized((cr.get('title') or [''])[0])).ratio()
        if similarity < 0.95:
            raise ValueError('OpenAlex/Crossref title mismatch; source needs review')
        if normalize_doi(cr['DOI']) != doi:
            raise ValueError('Crossref DOI mismatch')
        sources[item['id']] = dict(id=item['id'], doi=doi, url='https://doi.org/'+doi, title=work['display_name'],
            abstract=abstract_from_index(work.get('abstract_inverted_index')), source_type='Scientific publication',
            openalex_api_url=endpoint, crossref_api_url=crossref_url, crossref_title=(cr.get('title') or [''])[0],
            retrieved_at_utc=datetime.now(timezone.utc).isoformat(), raw_openalex=work, raw_crossref=cr)
    events = []
    for seed in config['events']:
        event = {field: None for field, _ in SCHEMA.values()}
        event.update(seed)
        event.update(record_kind='pollution_incident', longitude=None, longitude_role=None)
        for field, entries in event.get('field_evidence', {}).items():
            for entry in entries:
                source = sources[entry['source_id']]
                if not entry.get('excerpt') or entry['excerpt'] not in source['title'] + '\n' + source['abstract']:
                    raise ValueError(f'Unverified excerpt for {event["event_id"]}.{field}')
        primary = sources[event['primary_source_id']]
        event['source_url'] = primary['url']
        event['source_type'] = 'Scientific publication'
        event['evidence_review_scope'] = 'Retrieved abstract/title statements; publication identity checked via Crossref; no full-text/ground-truth verification'
        validate_event(event)
        events.append(event)
    return deduplicate_events(events), sources


def csv_value(value):
    if value is None:
        return ''
    if isinstance(value, dict) and 'start' in value:
        return value['start'] + ('/' + value['end'] if value.get('end') else '')
    if isinstance(value, list):
        return ', '.join(value)
    if type(value) is bool:
        return 'true' if value else 'false'
    value = str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def write_incident_outputs(events, sources, output, schema=None):
    input_count = len(events)
    events = deduplicate_events(events)
    # Also check evidence on offline regeneration; IDs and quotes must remain resolvable.
    for event in events:
        for field, entries in event.get('field_evidence', {}).items():
            for entry in entries:
                s = sources[entry['source_id']]
                if entry['excerpt'] not in s['title'] + '\n' + s['abstract']:
                    raise ValueError(f'Citation excerpt not found: {field}')
    path = Path(output); path.mkdir(parents=True, exist_ok=True)
    with (path/'notion_import.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f); writer.writerow(SCHEMA)
        for e in events:
            writer.writerow([csv_value(e.get(field)) for field,_ in SCHEMA.values()])
    (path/'notion_events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (path/'research_evidence.json').write_text(json.dumps({'sources':sources,'events':{e['event_id']:{'field_evidence':e['field_evidence'],'area_evidence':e.get('area_evidence'),'disagreements':e.get('disagreements',[])} for e in events}},ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    plan = dry_run(events, schema)
    (path/'notion_dry_run.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    stats = {'incidents':len(events), 'input_events':input_count, 'duplicates_removed':input_count-len(events), 'duplicate_event_ids':len(events)-len({e['event_id'] for e in events}),
        'satellite_images_confirmed_available':sum(e.get('satellite_image_available') is True for e in events),
        'satellite_image_availability_unknown':sum(e.get('satellite_image_available') is None for e in events),
        'classifier_candidates':sum(e.get('classifier_candidate') is True for e in events),
        'missing_values_by_column':{name:sum(e.get(field) is None for e in events) for name,(field,_) in SCHEMA.items()},
        'columns':list(SCHEMA),'schema_validation':plan['schema_validation']}
    (path/'validation.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
    lines=['# MAPDIS-AI pollution incident research','',f"Collected {len(events)} real, individually identified marine pollution events. These are incidents described by cited publications, not publication records relabeled as events.",'',
        'Citation identities and quoted title/abstract statements were checked against live OpenAlex/Crossref responses. This does not independently validate scientific claims or replace full-text review.','',
        '## Incident findings','']
    for e in events:
        lines += [f"### {e['event_name']}",'']
        for name,(field,_) in SCHEMA.items():
            value=e.get(field)
            if value is None:
                lines.append(f'- {name}: unknown.')
                continue
            refs=e.get('field_evidence',{}).get(field,[])
            cites=' '.join(f"[source]({sources[r['source_id']]['url']})" for r in refs)
            if field in {'notes','source_type','source_url'} and not cites:
                cites=f"[primary source]({e['source_url']})"
            lines.append(f'- {name}: {csv_value(value)}. {cites}')
        lines += ['', 'Evidence excerpts:','']
        for field, entries in e['field_evidence'].items():
            for r in entries:
                lines += [f"- **{field}**: {r['excerpt']} [citation]({sources[r['source_id']]['url']})"]
        lines += ['']
    lines += ['## Disagreements and limits', '']
    for e in events:
        for disagreement in e.get('disagreements', []):
            cites = ' '.join(f"[citation]({sources[sid]['url']})" for sid in disagreement['source_ids'])
            lines += [disagreement['text'] + ' ' + cites, '']
    lines += [
        'Any date-range area estimate applies to its stated observational interval, not a permanent event-wide footprint. Dates describe published observational periods and do not assert every day had an image. Unknown event-day dates remain null; years/seasons are retained in notes. Mass/volume are not used as surface area.','',
        'Published use of satellite images is recorded as documented imagery, but availability stays unknown until an identified image asset is verified. No asset access or incident bounding box was verified. Candidate classifier use means evidence review may be worthwhile, not a ready training dataset.','',
        'Notion Select/Multi-select option names require the actual schema. Exported semantic labels are proposals, not validated option names. All synchronization is disabled. Blank CSV checkbox cells mean unknown in the accompanying JSON; CSV import into Notion may coerce blanks to unchecked and cannot preserve tri-state meaning. Do not import until reviewing this loss and schema validation.','',
        f"Statistics: {json.dumps({k:v for k,v in stats.items() if k not in {'columns','missing_values_by_column'}},ensure_ascii=False)}"]
    (path/'research_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return stats
