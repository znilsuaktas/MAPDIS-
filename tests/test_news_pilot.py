import csv
import json
import pytest
from mapdis_research.pilot import build_sample,write_pilot,evaluate_reviews,load_pilot_config,collect_news
from mapdis_research.__main__ import main


def config(n=50):
    return dict(target_records=n,lookback_days=60,max_records_per_query=100,max_per_domain=15,request_interval_seconds=5,queries=[{'topic':'oil','query':'oil spill sea'}])


def raw(count=100):
    return [dict(article={'title':f'Oil spill at sea {i}','url':f'https://news{i%10}.example/story/{i}','seendate':'20261016090000','sourcecountry':'UK','language':'English'},topic='oil' if i%2 else 'plastic',query='marine pollution',retrieved_at_utc='2026-10-16T10:00:00+00:00') for i in range(count)]


def test_pilot_retains_unrelated_for_honest_evaluation():
    data=raw();data[0]['article']['title']='Unrelated politics'
    records,stats=build_sample(data,config())
    assert len(records)==50
    assert any(not r['pollution_assessment']['marine_pollution_relevant'] for r in records)
    assert all(r['event_date'] is None and r['country'] is None for r in records)
    assert all(r['publication_date'] is None and r['gdelt_seen_at'] for r in records)
    assert stats['precision'] is None and stats['human_reviewed']==0


def test_url_dedup_and_source_cap():
    data=raw(80);data.append(data[0])
    records,stats=build_sample(data,config())
    assert stats['duplicate_urls_removed']==1
    assert len({r['url'] for r in records})==len(records)
    assert max(stats['by_domain'].values())<=15


def test_shortfall_never_filled_with_papers():
    records,stats=build_sample(raw(3),config(100))
    assert len(records)==3 and stats['shortfall']==97
    assert all(r['source']=='gdelt_news' and r['verified_incident'] is False for r in records)


def test_pilot_csv_json_and_review_denominator(tmp_path):
    metrics=write_pilot(raw(),[],config(),tmp_path)
    assert metrics['sample_count']==50
    assert len(json.loads((tmp_path/'news_sample.json').read_text()))==50
    result=evaluate_reviews(tmp_path/'quality_review.csv')
    assert result['human_relevance_reviewed']==0
    assert result['algorithm_precision_on_reviewed_predictions'] is None
    with (tmp_path/'quality_review.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    rows[0]['human_relevance']='yes';rows[1]['human_relevance']='no'
    with (tmp_path/'reviewed.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    result=evaluate_reviews(tmp_path/'reviewed.csv')
    assert result['human_relevance_reviewed']==2 and result['relevant_fraction']==0.5
    assert result['notion_writes']==0


def test_review_invalid_labels_rejected(tmp_path):
    write_pilot(raw(),[],config(),tmp_path)
    p=tmp_path/'quality_review.csv'
    # Duplicate identifiers cannot inflate the reviewed denominator.
    with p.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
    rows[1]['id']=rows[0]['id']
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    with pytest.raises(ValueError):evaluate_reviews(p)


def test_proxy_403_diagnosis_stops_repeated_requests(monkeypatch):
    import requests
    calls=[]
    def fail(*a,**k):
        calls.append(1)
        raise requests.exceptions.ProxyError('Tunnel connection failed: 403 Forbidden')
    monkeypatch.setattr('mapdis_research.pilot.Client.get',fail)
    settings=config();settings['queries']*=4
    rows,status=collect_news(settings)
    assert not rows and len(calls)==1
    assert status[0]['error_origin']=='cloud_proxy_CONNECT_403'


def test_existing_outputs_not_overwritten(tmp_path):
    write_pilot(raw(),[],config(),tmp_path)
    before=(tmp_path/'news_sample.json').read_bytes()
    with pytest.raises(ValueError):write_pilot([],[],config(),tmp_path)
    assert (tmp_path/'news_sample.json').read_bytes()==before


def test_pilot_cli_handles_shortfall_honestly(tmp_path,monkeypatch):
    monkeypatch.setattr('mapdis_research.pilot.collect_news',lambda c:(raw(3),[]))
    assert main(['news-pilot','--output',str(tmp_path/'new')])==1
    assert main(['review-pilot','--input',str(tmp_path/'new/quality_review.csv')])==0


@pytest.mark.parametrize('field,value',[('target_records',49),('target_records',1000),('lookback_days',100),('max_records_per_query',1000),('request_interval_seconds',0)])
def test_bounded_pilot_settings(tmp_path,field,value):
    c=config();c[field]=value
    p=tmp_path/'config.json';p.write_text(json.dumps(c))
    with pytest.raises(ValueError):load_pilot_config(p)
