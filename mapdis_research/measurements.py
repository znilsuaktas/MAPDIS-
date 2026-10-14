"""Conservative source-only extraction; no geocoding or LLM inference."""
import math
import re

NUM = r"[+-]?\d+(?:\.\d+)?"
LONGITUDE = re.compile(rf"\b(?P<kind>incident(?: location)?|pollution(?: area)? centroid)\s+longitude\s*(?:is|:|=)?\s*(?P<value>{NUM})\s*°?\s*(?P<direction>[EW])?\b", re.I)
AREA = re.compile(rf"\b(?:pollution[- ]affected (?:surface )?area|oil[- ]spill (?:surface )?area|oil spill covered)\s*(?:is|was|of|:|=)?\s*(?P<uncertainty>approximately|about|estimated(?: at)?|~)?\s*(?P<value>{NUM})\s*(?P<unit>km²|km2|square kilometers?|square kilometres?|m²|m2|square meters?|square metres?|hectares?|ha|acres?)\b", re.I)
FACTORS = {'km²': 1, 'km2': 1, 'm²': 0.000001, 'm2': 0.000001, 'ha': 0.01, 'hectare': 0.01, 'hectares': 0.01, 'acre': 0.0040468564224, 'acres': 0.0040468564224}


def finite_number(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high


def extract_measurements(record):
    text, source = record.get('text', ''), record.get('url')
    evidence = {'longitude': [], 'estimated_area': []}
    for match in LONGITUDE.finditer(text):
        raw = match.group('value'); value = float(raw); direction = (match.group('direction') or '').upper()
        reason = None
        if direction:
            if raw.startswith(('+', '-')):
                reason = 'signed value with hemisphere is ambiguous'
            value = abs(value) * (-1 if direction == 'W' else 1)
        if not finite_number(value, -180, 180):
            reason = 'outside longitude range'
        tail = text[match.end():match.end()+40]
        before = text[max(0, match.start()-35):match.start()]
        if re.match(r'\s*(?:±|\+/-|to\s+\d|[-–]\s*\d|or\s+\d)', tail) or re.search(r'\b(?:not|no|hypothetical|simulated|approximately|about)\s*$', before, re.I):
            reason = 'ambiguous or non-incident coordinate'
        kind = 'pollution_centroid' if 'centroid' in match.group('kind').lower() else 'incident_location'
        evidence['longitude'].append(dict(value=value, original_measurement=match.group(0), coordinate_role=kind,
                                          source_url=source, excerpt=match.group(0), rejection_reason=reason))
    for match in AREA.finditer(text):
        unit = match.group('unit').lower(); factor = FACTORS.get(unit)
        if factor is None:
            factor = 1 if 'kilomet' in unit else 0.000001
        value = float(match.group('value')); converted = value * factor
        # Reject ranges, competing units, and error bars rather than discard their bounds.
        tail = text[match.end():match.end()+40]
        before = text[max(0, match.start()-35):match.start()]
        ambiguous = bool(re.match(r'\s*(?:±|\+/-|to\s+\d|[-–]\s*\d|or\s+\d)', tail) or re.search(r'\b(?:not|no|hypothetical|simulated|study|survey)\s*$', before, re.I))
        reason = 'ambiguous or non-incident measurement' if ambiguous else None
        if not finite_number(converted, 0, float('inf')):
            reason = 'invalid surface area'
        evidence['estimated_area'].append(dict(value_km2=converted, original_value=value, original_unit=match.group('unit'),
                original_measurement=match.group(0), source_url=source, excerpt=match.group(0),
                uncertainty=match.group('uncertainty') or 'not stated', rejection_reason=reason))
    result = dict(record, longitude=None, longitude_role=None, estimated_area_km2=None, measurement_evidence=evidence)
    for key, field, value_key in [('longitude', 'longitude', 'value'), ('estimated_area', 'estimated_area_km2', 'value_km2')]:
        candidates = evidence[key]
        # Multiple claims (even equal numbers) may describe different incidents; abstain.
        if len(candidates) == 1 and source and not candidates[0]['rejection_reason']:
            result[field] = candidates[0][value_key]
            if key == 'longitude':
                result['longitude_role'] = candidates[0]['coordinate_role']
    validate_measurements(result)
    return result


def validate_measurements(record):
    longitude = record.get('longitude'); area = record.get('estimated_area_km2')
    if longitude is not None and not finite_number(longitude, -180, 180):
        raise ValueError('Longitude must be finite and between -180 and 180')
    if longitude is not None and record.get('longitude_role') not in {'incident_location', 'pollution_centroid'}:
        raise ValueError('Longitude requires a coordinate role')
    if area is not None and not finite_number(area, 0, float('inf')):
        raise ValueError('Estimated Area must be finite and nonnegative km²')
    for field, key in [('longitude', 'longitude'), ('estimated_area_km2', 'estimated_area')]:
        if record.get(field) is not None:
            items = record.get('measurement_evidence', {}).get(key, [])
            if len(items) != 1 or not items[0].get('source_url') or not items[0].get('excerpt') or items[0].get('rejection_reason'):
                raise ValueError('Non-null measurements require unambiguous source evidence')
            item = items[0]
            value_key = 'value' if field == 'longitude' else 'value_km2'
            if item.get(value_key) != record[field] or item['source_url'] != record.get('url') or item['excerpt'] not in record.get('text', ''):
                raise ValueError('Measurement must match its retrieved source evidence')
