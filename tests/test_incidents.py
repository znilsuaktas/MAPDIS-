import copy
import csv
import json
import pytest
from mapdis_research.incidents import validate_event, validate_date, deduplicate_events, write_incident_outputs
from mapdis_research.notion import SCHEMA, properties, dry_run, validate_schema, NotionExporter
from mapdis_research.__main__ import main

NAMES=['Event Name','Pollution Type','Event Date','Satellite Observation Date','Country','Sea / Region','Cause','Estimated Area','Image Type','Source','Useful for Classifier','Notes','Satellite Image Available','Bounding Box Possible','Source Type','Status']
KINDS=['title','select','date','date','rich_text','rich_text','select','rich_text','multi_select','url','select','rich_text','checkbox','checkbox','select','select']


def event():
    e={field:None for field,_ in SCHEMA.values()}
    e.update(event_id='test-incident',record_kind='pollution_incident',event_name='Test spill',source_url='https://example.org/spill',pollution_type='Oil spill',source_type='Scientific publication')
    e['field_evidence']={field:[{'source_id':'s','excerpt':'Test spill Oil spill'}] for field in ['event_name','pollution_type']}
    return e


def sources():
    return {'s':{'title':'Test spill Oil spill','abstract':'A source excerpt','url':'https://example.org/spill'}}


@pytest.mark.parametrize('name,kind',list(zip(NAMES,KINDS)))
def test_all_sixteen_property_names_types_order(name,kind):
    assert list(SCHEMA)==NAMES
    assert SCHEMA[name][1]==kind
    assert 'Longitude' not in SCHEMA


def test_unknown_checks_are_not_false():
    e=event();p=properties(e)
    assert e['satellite_image_available'] is None
    assert 'Satellite Image Available' not in p
    assert 'Bounding Box Possible' not in p
    assert dry_run([e])['schema_validation']['status']=='pending'


def test_all_sixteen_payload_properties_when_known():
    e=event()
    e.update(event_date={'start':'2021-01-01'},satellite_observation_date={'start':'2021-01-02','end':'2021-01-05'},country='Test country',sea_region='Test sea',cause='Unknown cause label',estimated_area='2 ha',image_type=['SAR'],useful_for_classifier='Needs review',notes='Test',satellite_image_available=True,bounding_box_possible=True,status='Needs review')
    e['imagery_assets']=[{'url':'https://example.org/image'}];e['bounding_box']=[10,20,11,21]
    for field in ['event_date','satellite_observation_date','country','sea_region','cause','estimated_area','image_type','satellite_image_available','bounding_box_possible']:
        e['field_evidence'][field]=[{'source_id':'s','excerpt':'Test spill Oil spill'}]
    p=properties(e)
    assert list(p)==NAMES
    assert [next(iter(p[n])) for n in NAMES]==KINDS
    assert p['Estimated Area']['rich_text'][0]['text']['content']=='2 ha'
    assert p['Satellite Observation Date']['date']['end']=='2021-01-05'


def test_actual_options_rejected_unless_present():
    e=event()
    schema={'properties':{name:{'type':kind,kind:{'options':[]}} for name,(_,kind) in SCHEMA.items()}}
    assert validate_schema(schema,[e])['status']=='invalid'
    schema['properties']['Pollution Type']['select']['options']=[{'name':'Oil spill'}]
    schema['properties']['Source Type']['select']['options']=[{'name':'Scientific publication'}]
    assert validate_schema(schema,[e])['status']=='valid'
    schema['properties']['Estimated Area']['type']='number'
    assert validate_schema(schema,[e])['status']=='invalid'


def test_multi_select_actual_options():
    e=event();e['image_type']=['SAR'];e['field_evidence']['image_type']=e['field_evidence']['pollution_type']
    schema={'properties':{name:{'type':kind,kind:{'options':[{'name':v} for v in ['Oil spill','Scientific publication']]}} for name,(_,kind) in SCHEMA.items()}}
    assert any('SAR' in s for s in validate_schema(schema,[e])['errors'])
    schema['properties']['Image Type']['multi_select']['options']=[{'name':'SAR'}]
    assert validate_schema(schema,[e])['status']=='valid'


def test_incident_dedup_not_paper_dedup():
    e=event()
    assert len(deduplicate_events([e,copy.deepcopy(e)]))==1
    second=copy.deepcopy(e);second['event_id']='another-incident';second['event_name']='Another spill'
    assert len(deduplicate_events([e,second]))==2  # Same source can describe two incidents.
    conflicting=copy.deepcopy(e);conflicting['notes']='Different claim'
    with pytest.raises(ValueError):deduplicate_events([e,conflicting])


def test_research_papers_rejected():
    with pytest.raises(ValueError):properties({'title':'Paper about spills','doi':'10.123/example'})
    e=event();e['record_kind']='academic_paper'
    with pytest.raises(ValueError):validate_event(e)


@pytest.mark.parametrize('field', ['satellite_image_available','bounding_box_possible','classifier_candidate'])
def test_no_unsupported_boolean(field):
    e=event();e[field]=True
    with pytest.raises(ValueError):validate_event(e)


def test_no_mass_as_surface_area():
    e=event();e['estimated_area']='1000 tons';e['field_evidence']['estimated_area']=e['field_evidence']['pollution_type']
    with pytest.raises(ValueError):validate_event(e)


def test_invalid_dates_and_preserved_ranges():
    with pytest.raises(ValueError):validate_date({'start':'2021-02-30'})
    with pytest.raises(ValueError):validate_date({'start':'2021-05-01','end':'2021-04-01'})
    validate_date({'start':'2021-05-01','end':'2021-06-01'})


def test_csv_json_reports_and_citations(tmp_path):
    e=event();stats=write_incident_outputs([e,e],sources(),tmp_path)
    assert stats['duplicates_removed']==1
    with (tmp_path/'notion_import.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.reader(f))
    assert rows[0]==NAMES and len(rows)==2 and all(len(row)==16 for row in rows)
    assert rows[1][12]=='' and rows[1][13]==''
    assert json.loads((tmp_path/'notion_events.json').read_text())[0]['satellite_image_available'] is None
    assert 'https://example.org/spill' in (tmp_path/'research_report.md').read_text()
    assert 'Test spill Oil spill' in (tmp_path/'research_evidence.json').read_text()
    for name in ['notion_dry_run.json','validation.json','research_report.md']:
        assert (tmp_path/name).is_file()


def test_citations_cannot_be_invented(tmp_path):
    e=event();e['field_evidence']['event_name'][0]['excerpt']='Invented claim'
    with pytest.raises(ValueError):write_incident_outputs([e],sources(),tmp_path)


def test_every_notion_write_disabled():
    with pytest.raises(PermissionError):NotionExporter().export([event()])
    assert main(['notion-export','--notion-write'])==2


def test_incident_notion_cli_dry_run(tmp_path):
    src=tmp_path/'events.json';src.write_text(json.dumps([event()]))
    assert main(['notion-export','--input',str(src),'--output',str(tmp_path/'out')])==0
    plan=json.loads((tmp_path/'out/notion_dry_run.json').read_text())
    assert plan['mode']=='dry_run'
    assert plan['schema_validation']['writes_enabled'] is False


def test_live_collector_contract_with_mocked_sources(tmp_path,monkeypatch):
    from mapdis_research.incidents import collect_incidents
    config={'sources':[{'id':'s','doi':'10.123/example'}],'events':[dict(event(),primary_source_id='s')]}
    path=tmp_path/'config.json';path.write_text(json.dumps(config))
    class Response:
        def __init__(self,data):self.data=data
        def json(self):return self.data
    def get(self,url,**kwargs):
        if 'openalex' in url:
            return Response({'doi':'https://doi.org/10.123/example','display_name':'Test spill Oil spill','abstract_inverted_index':{'Test':[0],'spill':[1],'Oil':[2],'spill.':[3]},'is_retracted':False})
        return Response({'message':{'DOI':'10.123/example','title':['Test spill Oil spill']}})
    monkeypatch.setattr('mapdis_research.incidents.Client.get',get)
    events,s=collect_incidents(path)
    assert events[0]['record_kind']=='pollution_incident'
    assert events[0]['event_date'] is None
    assert s['s']['doi']=='10.123/example'
    config['events'][0]['field_evidence']['event_name'][0]['excerpt']='Nonexistent claim'
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):collect_incidents(path)


def test_publication_date_not_used_as_event_date(tmp_path):
    e=event();write_incident_outputs([e],sources(),tmp_path)
    result=json.loads((tmp_path/'notion_events.json').read_text())[0]
    assert result['event_date'] is None


def test_csv_area_original_unit_and_iso_interval(tmp_path):
    e=event();e['estimated_area']='12,741.94 ha';e['satellite_observation_date']={'start':'2021-03-10','end':'2021-06-06'}
    for field in ['estimated_area','satellite_observation_date']:
        e['field_evidence'][field]=[{'source_id':'s','excerpt':'A source excerpt'}]
    write_incident_outputs([e],sources(),tmp_path)
    with (tmp_path/'notion_import.csv').open(encoding='utf-8-sig',newline='') as f:
        row=next(csv.DictReader(f))
    assert row['Estimated Area']=='12,741.94 ha'
    assert row['Satellite Observation Date']=='2021-03-10/2021-06-06'


def test_invalid_new_mapping_cannot_invent_longitude(tmp_path):
    from mapdis_research.notion import DEFAULT_MAPPING,load_mapping
    mapping=dict(DEFAULT_MAPPING,longitude='Longitude');p=tmp_path/'mapping.json';p.write_text(json.dumps(mapping))
    with pytest.raises(ValueError):load_mapping(p)


def test_read_schema_is_only_get(monkeypatch):
    from mapdis_research.notion import read_schema
    monkeypatch.setenv('NOTION_TOKEN','fake-test-token');monkeypatch.setenv('NOTION_DATABASE_ID','db-123')
    calls=[]
    class Response:
        is_redirect=False
        def raise_for_status(self):pass
        def json(self):return {'properties':{}}
    def get(url,**kwargs):
        calls.append(url)
        assert kwargs['allow_redirects'] is False
        return Response()
    monkeypatch.setattr('mapdis_research.notion.requests.get',get)
    assert read_schema()=={'properties':{}}
    assert len(calls)==1 and calls[0].endswith('/databases/db-123')
