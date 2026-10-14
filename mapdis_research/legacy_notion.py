"""Optional create-only Notion export. Existing pages are never patched."""
import json
import time
import requests
from .measurements import extract_measurements

DEFAULT_MAPPING = {
    'title': 'Title', 'date': 'Date', 'url': 'URL', 'doi': 'DOI', 'source': 'Source',
    'keyword_matches': 'Keyword Matches', 'score': 'Relevance Score',
    'supporting_excerpt': 'Supporting Excerpt', 'longitude': 'Longitude',
    'estimated_area_km2': 'Estimated Area',
}
TYPES = dict(title='title', date='date', url='url', doi='rich_text', source='rich_text',
             keyword_matches='rich_text', score='number', supporting_excerpt='rich_text',
             longitude='number', estimated_area_km2='number')


def load_mapping(path=None):
    if path:
        with open(path, encoding='utf-8') as f:
            mapping = json.load(f)
    else:
        mapping = dict(DEFAULT_MAPPING)
    if set(mapping) != set(DEFAULT_MAPPING) or any(not isinstance(v, str) or not v.strip() for v in mapping.values()) or len(set(mapping.values())) != 10:
        raise ValueError('Notion mapping requires 10 distinct property names')
    return mapping


def properties(record, mapping=None):
    mapping = mapping or DEFAULT_MAPPING
    record = extract_measurements(record)  # Never trust imported numeric fields alone.
    props = {}
    for field, name in mapping.items():
        value = record.get(field); kind = TYPES[field]
        if field == 'keyword_matches':
            value = '; '.join(value or [])
        if kind in {'title', 'rich_text'}:
            props[name] = {kind: [{'text': {'content': str(value)[:2000]}}] if value is not None else []}
        elif kind == 'date':
            props[name] = {'date': {'start': value} if value else None}
        else:
            props[name] = {kind: value}
    return props


class NotionExporter:
    def __init__(self, token, database_id, mapping=None):
        if not token or not database_id:
            raise ValueError('NOTION_TOKEN and NOTION_DATABASE_ID are required for write mode')
        self.database_id = database_id
        self.mapping = mapping or DEFAULT_MAPPING
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {token}', 'Notion-Version': '2022-06-28'})

    def request(self, method, path, **kwargs):
        time.sleep(0.4)
        response = self.session.request(method, 'https://api.notion.com/v1/' + path, timeout=30, allow_redirects=False, **kwargs)
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError('Notion redirects are not permitted')
        return response.json()

    def export(self, records):
        raise PermissionError("Legacy academic Notion writes are disabled; use incident dry-run exports")
