import json
import pytest
from mapdis_research.context import assess
from mapdis_research.processing import process
from mapdis_research.config import load_config
from mapdis_research.feeds import parse_feed
from mapdis_research.sources import discover


def record(text,source='rss'):
    return dict(title='Environmental report',text=text,source=source,url='https://example.org/report',doi=None,date='2026-10-01',source_quality=0.7)


@pytest.mark.parametrize('text,category',[
 ('A tanker leaked diesel into the sea.','oil'),
 ('Untreated sewage was discharged into the harbour.','wastewater'),
 ('Chemical waste was dumped on the coast.','chemical'),
 ('Plastic pellets washed ashore on the beach.','plastic'),
 ('Marmara sahilinde müsilaj tespit edildi.','mucilage'),
 ('Arıtılmamış atık su denize boşaltıldı.','wastewater'),
 ('Balık ölümleri sahilde tespit edildi.','unclassified'),
])
def test_sensor_free_pollution_candidates(text,category):
    r=record(text);a=assess(r)
    assert a['marine_pollution_relevant']
    assert category in a['pollution_categories']
    assert a['record_kind']=='incident_candidate'
    assert a['verified_incident'] is False
    assert a['supporting_excerpts']
    config=load_config('config/advanced.json','marine_pollution')
    assert len(process([r],config))==1


@pytest.mark.parametrize('text',[
 'A port may cause sewage pollution in the sea.',
 'No pollution was detected on the coast.',
 'Denizde kirlilik tespit edilmedi.',
 'A simulation predicted an oil spill in the sea.',
])
def test_uncertain_or_negated_is_not_confirmed_incident(text):
    a=assess(record(text))
    assert a['record_kind']!='incident_candidate'
    assert not a['verified_incident']


@pytest.mark.parametrize('text',['Sentinel-1 detected a landslide in the mountains.','Soil contamination at an inland factory.','Air pollution on the coast worsened.'])
def test_irrelevant_or_sensor_only_rejected(text):
    assert not assess(record(text))['marine_pollution_relevant']
    assert process([record(text)],load_config('config/advanced.json','marine_pollution'))==[]


def test_academic_paper_not_disguised_as_incident():
    a=assess(record('We detected sewage discharge along the coast.',source='openalex'))
    assert a['marine_pollution_relevant'] and a['record_kind']=='academic_research'


def test_rss_and_atom_parsing():
    rss='<rss><channel><item><title>Sewage discharged into sea</title><link>https://example.org/story</link><pubDate>Fri, 16 Oct 2026 08:00:00 GMT</pubDate><description>Untreated sewage reached the coast.</description></item></channel></rss>'
    rows=parse_feed(rss,'https://example.org/feed')
    assert rows[0]['date']=='2026-10-16' and rows[0]['content_scope']=='feed_summary_only'
    assert assess(rows[0])['record_kind']=='incident_candidate'
    atom='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Plastic on beach</title><link href="https://example.org/plastic"/><published>2026-10-15T12:00:00Z</published><summary>Plastic pellets washed ashore.</summary></entry></feed>'
    assert parse_feed(atom,'https://example.org/feed')[0]['date']=='2026-10-15'


def test_missing_feed_date_stays_unknown():
    rows=parse_feed('<rss><channel><item><title>Oil spill</title><link>https://example.org/a</link></item></channel></rss>','https://example.org/feed')
    assert rows[0]['date'] is None


def test_feed_terms_and_robots_enforced():
    class Deny:
        def allowed(self,url):return False
        def get(self,*a,**k):raise AssertionError('Must not request denied feed')
    source={'type':'rss','url':'https://example.org/feed'}
    with pytest.raises(PermissionError):discover(Deny(),{},source)
    with pytest.raises(PermissionError):discover(Deny(),{},dict(source,terms_reviewed=True))


def test_feed_entities_rejected():
    with pytest.raises(ValueError):parse_feed('<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>','https://example.org/feed')


def test_missing_feed_url_is_not_invented():
    assert parse_feed('<rss><channel><item><title>Oil spill at sea</title></item></channel></rss>','https://example.org/feed')==[]


def test_doi_paper_from_website_stays_academic():
    r=record('Oil was spilled into the sea.',source='website');r['doi']='10.123/test'
    assert assess(r)['record_kind']=='academic_research'


def test_candidate_outputs_are_separate_from_notion_incidents(tmp_path):
    from mapdis_research.report import write_outputs
    r=record('Sewage was discharged into the sea.')
    records=process([r],load_config('config/advanced.json','marine_pollution'))
    write_outputs(records,tmp_path,[])
    assert len(json.loads((tmp_path/'incident_candidates.json').read_text())['records'])==1
    assert json.loads((tmp_path/'academic_notion_preview.json').read_text())==[]
    assert 'incident_candidate' in (tmp_path/'report.md').read_text()
