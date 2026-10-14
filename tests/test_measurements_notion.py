import json
import math
import pytest
from mapdis_research.measurements import extract_measurements, validate_measurements
from mapdis_research.legacy_notion import properties, DEFAULT_MAPPING, TYPES, NotionExporter, load_mapping
from mapdis_research.report import write_outputs
from mapdis_research.__main__ import main


def record(text):
    return dict(title='Oil spill', date='2024-01-01', url='https://example.org/incident', text=text,
                doi='10.123/example', source='website', source_quality=0.8, score=0.9,
                keyword_matches=['oil spill'], supporting_excerpt=text)


@pytest.mark.parametrize('text,value,role', [
    ('Incident longitude: 23.4 E',23.4,'incident_location'),
    ('Incident location longitude: 180 W',-180,'incident_location'),
    ('Pollution area centroid longitude: -12.5',-12.5,'pollution_centroid'),
    ('Incident longitude: 181 E',None,None),
    ('Incident longitude: -30 W',None,None),
    ('Incident longitude: 30 E or 40 E',None,None),
    ('Approximately incident longitude: 30 E',None,None),
    ('Study boundary: 12 E to 25 E',None,None),
    ('Incident longitude: 12 E; incident longitude: 13 E',None,None),
])
def test_longitude(text,value,role):
    result=extract_measurements(record(text))
    assert result['longitude']==value
    assert result['longitude_role']==role


@pytest.mark.parametrize('text,value',[
    ('Pollution-affected surface area: approximately 250 hectares',2.5),
    ('Oil spill area: 1000000 m²',1),
    ('Oil spill covered 3 km²',3),
    ('Oil spill area: 1 acre',0.0040468564224),
    ('Oil spill volume: 1000 m³; spilled oil mass: 200 tonnes',None),
    ('Study area: 100 km²',None),
    ('Oil spill area: 10 km² ± 2 km²',None),
    ('Oil spill area: -5 km²',None),
    ('Oil spill area: 10 to 20 km²',None),
    ('Oil spill area: 3 km². Oil spill area: 4 km².',None),
])
def test_area(text,value):
    r=extract_measurements(record(text))
    assert r['estimated_area_km2']==value
    if value is not None:
        e=r['measurement_evidence']['estimated_area'][0]
        assert e['original_unit'] and e['original_measurement'] in text
        assert e['source_url']==r['url']
        assert 'uncertainty' in e


@pytest.mark.parametrize('value',[181,-181,float('nan'),float('inf'),True,'12'])
def test_invalid_longitude(value):
    with pytest.raises(ValueError):
        validate_measurements({'longitude':value,'longitude_role':'incident_location'})


def test_export_all_properties_and_unknowns(tmp_path):
    r=record('Incident longitude: 30 W. Oil spill area: about 200 hectares')
    write_outputs([r],tmp_path,[])
    result=json.loads((tmp_path/'results.json').read_text())[0]
    assert result['longitude']==-30 and result['estimated_area_km2']==2
    assert 'longitude_role' in (tmp_path/'results.csv').read_text(encoding='utf-8-sig')
    assert 'about' in (tmp_path/'report.md').read_text()
    props=properties(r)
    assert len(props)==10 and props['Longitude']=={'number':-30}
    assert props['Estimated Area']=={'number':2}
    assert properties(record('Spilled 200 barrels'))['Estimated Area']=={'number':None}
    assert properties(dict(r,longitude=123))['Longitude']=={'number':-30}


def test_custom_mapping_and_dry_run(tmp_path):
    mapping=dict(DEFAULT_MAPPING,longitude='Incident Longitude')
    m=tmp_path/'mapping.json';m.write_text(json.dumps(mapping))
    assert load_mapping(m)==mapping
    assert 'Incident Longitude' in properties(record(''),mapping)
    inp=tmp_path/'records.json';inp.write_text(json.dumps([record('')]))
    assert main(['notion-export','--input',str(inp),'--mapping',str(m),'--output',str(tmp_path/'export')])==2
    assert not (tmp_path/'export/notion_pages.json').exists()


def test_existing_notion_pages_never_modified(monkeypatch):
    exporter=NotionExporter('test-token','test-db')
    calls=[]
    def request(method,path,**kwargs):
        calls.append((method,path))
        if method=='GET':
            return {'properties':{name:{'type':TYPES[field]} for field,name in DEFAULT_MAPPING.items()}}
        if path.endswith('/query'):
            return {'results':[{'id':'existing'}]}
        raise AssertionError('Existing record must not be written')
    monkeypatch.setattr(exporter,'request',request)
    with pytest.raises(PermissionError):
        exporter.export([record('')])
    assert not any(method=='PATCH' or path=='pages' for method,path in calls)


def test_create_notion_page_with_new_fields(monkeypatch):
    exporter=NotionExporter('test-token','test-db');payloads=[]
    def request(method,path,**kwargs):
        if method=='GET':
            return {'properties':{name:{'type':TYPES[field]} for field,name in DEFAULT_MAPPING.items()}}
        if path.endswith('/query'):
            return {'results':[]}
        assert method=='POST' and path=='pages'
        payloads.append(kwargs['json']);return {'id':'new'}
    monkeypatch.setattr(exporter,'request',request)
    with pytest.raises(PermissionError):
        exporter.export([record('Incident longitude: -20. Oil spill area: 2 km²')])
    assert payloads==[]


def test_bad_schema_prevents_writes(monkeypatch):
    exporter=NotionExporter('test-token','test-db')
    monkeypatch.setattr(exporter,'request',lambda *a,**k:{'properties':{}})
    with pytest.raises(PermissionError):
        exporter.export([record('')])


@pytest.mark.parametrize('value',[-1,float('nan'),float('inf'),True,'5'])
def test_invalid_area(value):
    with pytest.raises(ValueError):
        validate_measurements({'estimated_area_km2':value})


def test_forged_evidence_rejected():
    r=extract_measurements(record('Incident longitude: 20 E'))
    r['longitude']=30
    with pytest.raises(ValueError):
        validate_measurements(r)


def test_area_uncertainty_preserved():
    r=extract_measurements(record('Pollution-affected surface area: approximately 250 hectares'))
    e=r['measurement_evidence']['estimated_area'][0]
    assert e['original_value']==250
    assert e['original_unit']=='hectares'
    assert e['uncertainty']=='approximately'
    assert e['value_km2']==2.5
