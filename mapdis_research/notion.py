"""Confirmed incident schema. No create, update, delete, or sync operations."""
import json
import os
import requests

# Dict insertion order is the user-confirmed column/property order.
SCHEMA = {
    'Event Name': ('event_name', 'title'),
    'Pollution Type': ('pollution_type', 'select'),
    'Event Date': ('event_date', 'date'),
    'Satellite Observation Date': ('satellite_observation_date', 'date'),
    'Country': ('country', 'rich_text'),
    'Sea / Region': ('sea_region', 'rich_text'),
    'Cause': ('cause', 'select'),
    'Estimated Area': ('estimated_area', 'rich_text'),
    'Image Type': ('image_type', 'multi_select'),
    'Source': ('source_url', 'url'),
    'Useful for Classifier': ('useful_for_classifier', 'select'),
    'Notes': ('notes', 'rich_text'),
    'Satellite Image Available': ('satellite_image_available', 'checkbox'),
    'Bounding Box Possible': ('bounding_box_possible', 'checkbox'),
    'Source Type': ('source_type', 'select'),
    'Status': ('status', 'select'),
}
DEFAULT_MAPPING = {field: name for name, (field, _) in SCHEMA.items()}
TYPES = {field: kind for name, (field, kind) in SCHEMA.items()}


def load_mapping(path=None):
    mapping = dict(DEFAULT_MAPPING)
    if path:
        with open(path, encoding='utf-8') as f:
            supplied = json.load(f)
        if supplied != mapping or list(supplied) != list(mapping):
            raise ValueError('Mapping must match the confirmed 16 properties and order')
    return mapping


def read_schema():
    token, database = os.environ.get('NOTION_TOKEN'), os.environ.get('NOTION_DATABASE_ID')
    if not token or not database:
        raise ValueError('Schema read requires NOTION_TOKEN and NOTION_DATABASE_ID; no values should be entered in chat')
    if not all(c.isalnum() or c == '-' for c in database):
        raise ValueError('Invalid Notion database identifier')
    response = requests.get('https://api.notion.com/v1/databases/' + database, timeout=30, allow_redirects=False,
                            headers={'Authorization': 'Bearer ' + token, 'Notion-Version': '2022-06-28'})
    response.raise_for_status()
    if response.is_redirect:
        raise ValueError('Notion schema redirects are disabled')
    return response.json()


def validate_schema(schema, events):
    props = schema.get('properties', schema)
    errors = []
    for name, (field, kind) in SCHEMA.items():
        actual = props.get(name, {})
        if actual.get('type') != kind:
            errors.append(f'{name}: expected {kind}')
            continue
        if kind in {'select', 'multi_select'}:
            allowed = {o['name'] for o in actual.get(kind, {}).get('options', [])}
            for event in events:
                value = event.get(field)
                values = value if isinstance(value, list) else [value]
                for option in values:
                    if option is not None and option not in allowed:
                        errors.append(f'{name}: unconfirmed option {option!r}')
    return {'status': 'valid' if not errors else 'invalid', 'errors': sorted(set(errors)),
            'writes_enabled': False, 'schema_origin': 'provided schema snapshot or read-only API'}


def properties(event, mapping=None):
    from .incidents import validate_event
    validate_event(event)
    if mapping is not None and mapping != DEFAULT_MAPPING:
        raise ValueError('Only the confirmed incident mapping is supported')
    props = {}
    for name, (field, kind) in SCHEMA.items():
        value = event.get(field)
        if kind == 'checkbox' and value is None:
            # Omitting unknown prevents falsely asserting false in an API payload.
            continue
        if kind in {'title', 'rich_text'}:
            if value is not None and len(value) > 2000:
                raise ValueError(f'{name} exceeds Notion rich-text limit')
            props[name] = {kind: [{'text': {'content': value}}] if value is not None else []}
        elif kind == 'date':
            props[name] = {'date': value}
        elif kind == 'select':
            props[name] = {'select': {'name': value} if value is not None else None}
        elif kind == 'multi_select':
            if value is not None:
                props[name] = {'multi_select': [{'name': v} for v in value]}
        else:
            props[name] = {kind: value}
    return props


def dry_run(events, schema=None):
    validation = validate_schema(schema, events) if schema else {
        'status': 'pending', 'errors': ['Actual Select/Multi-select options not supplied'], 'writes_enabled': False}
    return {'mode': 'dry_run', 'schema_validation': validation, 'confirmed_columns': list(SCHEMA),
            'unknown_checkbox_policy': 'omit API properties; blank CSV; null research JSON',
            'pages': [{'event_id': e['event_id'], 'properties': properties(e),
                       'unknown_fields': [field for field in DEFAULT_MAPPING if e.get(field) is None]} for e in events]}


class NotionExporter:
    """Compatibility guard: writes require a separate, explicitly approved task."""
    def __init__(self, *args, **kwargs):
        pass

    def export(self, records):
        raise PermissionError('Notion synchronization is dry-run only; no records may be written')
