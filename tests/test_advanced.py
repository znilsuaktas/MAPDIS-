import copy
import json
import pytest
import requests
from mapdis_research.config import load_config
from mapdis_research.matching import contains
from mapdis_research.sources import discover
from mapdis_research.processing import process
from mapdis_research.dashboard import write_dashboard
from mapdis_research.__main__ import main


def sample(**changes):
    return dict(dict(title='Oil spill Sentinel-1', date='2024-01-01', url='https://example.org/a', doi='10.123/a', text='An oil spill was mapped with SAR imagery.', source='openalex', source_quality=0.9), **changes)


def test_profiles_and_query_budget():
    for profile in ['oil_spill','plastic','mucilage','all']:
        c=load_config('config/advanced.json',profile)
        assert len(c['keywords'])>=40
        assert c['selected_profile']==profile
        assert len(c['queries'])<=6
    assert main(['plan','--profile','plastic','--max-queries','2','--pages','1'])==0
    assert main(['profiles'])==0


def test_unicode_phrase_matching():
    assert contains('SENTINEL–1 görüntüleri', 'Sentinel-1')
    assert contains('MÜSİLAJ ve petrol sızıntısı', 'müsilaj')
    assert contains('petrol SIZINTISI', 'petrol sızıntısı')
    assert not contains('soil contamination', 'oil')
    assert not contains('microplastics','plastic')


def test_required_groups_and_exclusions():
    c=load_config('config/advanced.json','oil_spill')
    r=process([sample(),sample(doi='10.123/b',url='https://example.org/b',title='Sentinel-1 landslide detection',text='Synthetic aperture radar')],c)
    assert len(r)==1 and 'oil' in r[0]['matched_groups']
    assert process([sample(text='oil spill soil contamination')],c)==[]


def test_query_pagination_and_partial_failure():
    class Response:
        def json(self):
            return {'results':[{'id':'https://openalex.org/W1','display_name':'Oil spill','publication_date':'2024-01-01','doi':'https://doi.org/10.123/a'}], 'meta':{'next_cursor':'second'}}
    class Client:
        diagnostics=[]
        def get(self,url,**kwargs):
            if kwargs['params']['page']==1:return Response()
            response=requests.Response();response.status_code=429
            raise requests.HTTPError(response=response)
    client=Client()
    r=discover(client,{'keywords':['oil spill'],'pages_per_query':3,'max_results_per_source':1},{'type':'openalex'})
    assert len(r)==1 and len(client.diagnostics)==2
    assert client.diagnostics[-1]['http_status']==429
    assert r[0]['discovery'][0]['page']==1


def test_crossref_cursor_pagination():
    class Response:
        def __init__(self,page):self.page=page
        def json(self):
            return {'message':{'items':[{'title':['Oil spill'],'DOI':f'10.123/{self.page}','URL':f'https://example.org/{self.page}'}],'next-cursor':'cursor2'}}
    class Client:
        diagnostics=[]
        def get(self,url,**kwargs):
            return Response(kwargs['params']['cursor'])
    c=Client()
    r=discover(c,{'keywords':['oil spill'],'pages_per_query':2,'max_results_per_source':1},{'type':'crossref'})
    assert len(r)==2
    assert r[1]['discovery'][0]['page']==2


def test_merge_source_provenance():
    a=sample(discovery=[{'source':'openalex','query':'oil spill','page':1}])
    b=sample(source='crossref',discovery=[{'source':'crossref','query':'Sentinel-1','page':2}])
    r=process([a,b],{'keywords':['oil spill']})
    assert len(r)==1 and len(r[0]['discovery'])==2
    assert set(r[0]['supporting_sources'])=={'openalex','crossref'}


def test_offline_replay_and_output_guard(tmp_path,monkeypatch):
    p=tmp_path/'raw.json';p.write_text(json.dumps([sample()]))
    def deny(*a,**k):raise AssertionError('Replay must not use network')
    monkeypatch.setattr('requests.Session.get',deny)
    out=tmp_path/'out'
    assert main(['replay','--input',str(p),'--output',str(out)])==0
    assert (out/'dashboard.html').is_file()
    config=json.loads((out/'effective_config.json').read_text())
    assert load_config(out/'effective_config.json')['keywords']==config['keywords']
    assert json.loads((out/'summary.json').read_text())['mode']=='offline_replay'
    before=(out/'results.json').read_bytes()
    assert main(['replay','--input',str(p),'--output',str(out)])==2
    assert (out/'results.json').read_bytes()==before


def test_dashboard_escapes_source_html(tmp_path):
    write_dashboard([sample(title='<script>alert(1)</script>', url='javascript:alert(1)')],tmp_path)
    text=(tmp_path/'dashboard.html').read_text()
    assert '<script>alert(1)</script>' not in text
    assert '&lt;script&gt;' in text
    assert 'href="javascript:' not in text


def test_repeated_cursor_stops():
    class Response:
        def json(self):return {'message':{'items':[{'title':['Oil spill'],'URL':'https://example.org/a'}],'next-cursor':'*'}}
    class Client:
        diagnostics=[]
        def get(self,*a,**k):return Response()
    c=Client()
    r=discover(c,{'keywords':['oil spill'],'pages_per_query':5,'max_results_per_source':1},{'type':'crossref'})
    assert len(r)<=2  # Repeated cursors cannot create an unbounded request loop.


def test_unknown_profile_rejected():
    with pytest.raises(ValueError):load_config('config/advanced.json','nonexistent')


@pytest.mark.parametrize('setting,value',[('pages_per_query',0),('pages_per_query',True),('max_queries',101),('max_results_per_source',True),('request_interval_seconds',float('nan'))])
def test_invalid_advanced_bounds(tmp_path,setting,value):
    config={'keywords':['oil spill'],'sources':[{'type':'openalex'}],setting:value}
    p=tmp_path/'config.json';p.write_text(json.dumps(config))
    with pytest.raises(ValueError):load_config(p)


def test_crossref_same_scroll_cursor_with_distinct_pages():
    class Response:
        def __init__(self,n):self.n=n
        def json(self):return {'message':{'items':[{'title':['Oil spill'],'DOI':f'10.123/{self.n}','URL':f'https://example.org/{self.n}'}],'next-cursor':'same-scroll-cursor'}}
    class Client:
        diagnostics=[]
        n=0
        def get(self,*a,**k):
            self.n+=1
            return Response(self.n)
    client=Client()
    r=discover(client,{'keywords':['oil spill'],'pages_per_query':3,'max_results_per_source':1},{'type':'crossref'})
    assert len(r)==3 and client.n==3
