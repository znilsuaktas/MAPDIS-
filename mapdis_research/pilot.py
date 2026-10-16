"""News-only pilot sampling and honest, manual-label-based evaluation.

GDELT supplies discovery metadata, not article bodies, publication dates or
independent verification. Publisher sites are not automatically fetched.
"""
import csv
import hashlib
import json
import logging
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from .context import assess
from .http import Client
from .matching import normalized
from .processing import canonical_url
from .dashboard import write_dashboard

log = logging.getLogger(__name__)
ENDPOINT = 'https://api.gdeltproject.org/api/v2/doc/doc'
REVIEW_FIELDS = ['human_relevance','human_incident','human_source_quality','human_evidence_sufficient','decision','reviewer_notes']


def load_pilot_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8'))
    for key,minimum,maximum in [('target_records',50,100),('lookback_days',1,89),('max_records_per_query',1,250),('max_per_domain',1,100)]:
        value=config.get(key)
        if type(value) is not int or not minimum<=value<=maximum:
            raise ValueError(f'{key} must be {minimum}..{maximum}')
    provider=config.get('provider','gdelt')
    if provider not in {'gdelt','rss'}:raise ValueError('Unknown news provider')
    if provider=='rss':
        feeds=config.get('feeds')
        if not isinstance(feeds,list) or not 1<=len(feeds)<=30:raise ValueError('RSS pilot requires 1..30 explicit feeds')
        for feed in feeds:
            if urlsplit(feed.get('url','')).scheme!='https' or not feed.get('topic'):raise ValueError('Each feed requires HTTPS URL and topic')
    if provider=='gdelt' and (not isinstance(config.get('queries'),list) or not 1<=len(config['queries'])<=20):
        raise ValueError('1..20 explicit pilot queries are required')
    for query in config.get('queries',[]):
        if not isinstance(query.get('query'),str) or not query['query'].strip() or not query.get('topic'):
            raise ValueError('Each query requires a topic and query string')
    interval=config.get('request_interval_seconds',5)
    if not isinstance(interval,(float,int)) or isinstance(interval,bool) or not 5<=interval<=300:
        raise ValueError('Pilot request interval must be 5..300 seconds')
    return config


def news_error_details(exc):
    """Expose useful status metadata, without logging headers/tokens or body."""
    response = getattr(exc, 'response', None)
    code = response.status_code if response is not None else None
    tunnel_denied = 'Tunnel connection failed: 403' in str(exc)
    origin = 'proxy_CONNECT_403' if tunnel_denied else 'http_response_origin_unverified' if code else 'transport_or_payload_error'
    hints = {
        401: 'API authentication/access rejected; check the provider requirements.',
        403: 'HTTP access denied. Could be provider/security gateway; this alone does not prove a Codex proxy block.',
        429: 'API rate limit reached. Wait for Retry-After if supplied; do not repeatedly rerun.',
    }
    hint = hints.get(code, 'Provider unavailable; retry later.' if code and code >= 500 else 'Inspect the status file; response did not produce a usable article list.')
    if tunnel_denied:
        hint = 'The configured HTTPS proxy rejected CONNECT before the API response. On Windows check local proxy/network policy; cloud settings do not change your PC.'
    def header(name):
        value = response.headers.get(name) if response is not None else None
        return ''.join(c for c in value[:120] if c.isprintable()) if value else None
    return dict(error_type=type(exc).__name__, http_status=code, error_origin=origin,
                retry_after=header('Retry-After'), response_server=header('Server'), troubleshooting_hint=hint)


def collect_news(config):
    if config.get('provider')=='rss':
        return collect_rss_news(config)
    client=Client(config)
    now=datetime.now(timezone.utc)
    statuses=[]; raw=[]
    for query in config['queries']:
        params=dict(query=query['query'],mode='artlist',format='json',maxrecords=config['max_records_per_query'],
                    startdatetime=(now-timedelta(days=config['lookback_days'])).strftime('%Y%m%d%H%M%S'),
                    enddatetime=now.strftime('%Y%m%d%H%M%S'),sort='datedesc')
        try:
            response=client.get(ENDPOINT,params=params)
            data=response.json()
            if not isinstance(data,dict) or not isinstance(data.get('articles'),list):
                raise ValueError('Expected GDELT article-list response')
            for article in data['articles']:
                raw.append({'article':article,'query':query['query'],'topic':query['topic'],
                            'retrieved_at_utc':now.isoformat(),'discovery_api':ENDPOINT})
            statuses.append(dict(topic=query['topic'],query=query['query'],status='success',count=len(data['articles'])))
        except Exception as exc:
            details = news_error_details(exc)
            statuses.append(dict(topic=query['topic'], status='failed', **details))
            log.error('News query failed: %s (%s; HTTP %s; origin=%s; Retry-After=%s)',
                      query['topic'], details['error_type'], details['http_status'] or 'unknown',
                      details['error_origin'], details['retry_after'] or 'not supplied')
            log.error('%s', details['troubleshooting_hint'])
            # No automatic repeated requests after rejection, rate limits or outages.
            code = details['http_status']
            if details['error_origin'] == 'proxy_CONNECT_403' or code in {401,403,429} or (code and code >= 500):
                break
    return raw,statuses


def collect_rss_news(config):
    """Independent RSS provider; never used to retry the rejected GDELT endpoint."""
    from .feeds import discover_feed
    client=Client(config)
    raw=[];statuses=[]
    for feed in config['feeds']:
        if not feed.get('enabled',False) or not feed.get('terms_reviewed',False):
            statuses.append(dict(topic=feed['topic'],source_url=feed['url'],status='review_required',count=0))
            log.warning('RSS source disabled pending explicit usage-terms review: %s',feed['url'])
            continue
        try:
            records=discover_feed(client,{'max_results_per_source':config['max_records_per_query']},dict(feed,type='rss'))
            now=datetime.now(timezone.utc).isoformat()
            cutoff=(datetime.now(timezone.utc)-timedelta(days=config['lookback_days'])).date().isoformat()
            outside_window=0
            for r in records:
                if r['date'] and r['date']<cutoff:
                    outside_window+=1
                    continue
                raw.append(dict(article={'title':r['title'],'url':r['url'],'publication_date':r['date'],'summary':r['text']},
                                provider='rss',topic=feed['topic'],query=feed['url'],retrieved_at_utc=now,feed_url=feed['url']))
            statuses.append(dict(topic=feed['topic'],source_url=feed['url'],status='success',count=len(records)-outside_window,outside_window=outside_window))
        except Exception as exc:
            details=news_error_details(exc)
            statuses.append(dict(topic=feed['topic'],source_url=feed['url'],status='failed',**details))
            log.error('RSS failed: %s (HTTP %s; %s)',feed['url'],details['http_status'] or 'unknown',details['error_type'])
    return raw,statuses


def build_sample(raw,config):
    by_url={}; rejected=0
    for envelope in raw:
        article=envelope.get('article',{})
        url=article.get('url','');title=article.get('title','')
        parts=urlsplit(url)
        if parts.scheme not in {'https','http'} or not parts.hostname or parts.username or not isinstance(title,str) or not title.strip():
            rejected+=1;continue
        url=canonical_url(url)
        provenance=dict(topic=envelope['topic'],query=envelope['query'])
        if url in by_url:
            if provenance not in by_url[url]['discovered_by']:by_url[url]['discovered_by'].append(provenance)
            continue
        provider=envelope.get('provider','gdelt')
        publication_date=article.get('publication_date') if provider=='rss' else None
        record=dict(id=hashlib.sha256(url.encode()).hexdigest()[:16],title=title.strip(),url=url,doi=None,date=publication_date,
                    publication_date=publication_date,gdelt_seen_at=article.get('seendate'),source='rss' if provider=='rss' else 'gdelt_news',
                    domain=parts.hostname.lower(),language=article.get('language'),publisher_country=article.get('sourcecountry'),
                    text=article.get('summary','') if provider=='rss' else '',source_quality=None,content_scope='feed_summary_only' if provider=='rss' else 'discovery_title_only',discovered_by=[provenance],
                    retrieved_at_utc=envelope.get('retrieved_at_utc'),article_body_checked=False,source_url_http_status=None,
                    event_date=None,country=None,longitude=None,estimated_area=None,verified_incident=False)
        record['pollution_assessment']=assess(record)
        # Source country is publisher metadata, never incident location.
        record['title_cluster']=hashlib.sha256(normalized(title).encode()).hexdigest()[:12]
        by_url[url]=record
    buckets=defaultdict(deque)
    for record in by_url.values():buckets[record['discovered_by'][0]['topic']].append(record)
    selected=[];domains=Counter()
    while any(buckets.values()) and len(selected)<config['target_records']:
        progressed=False
        for topic in buckets:
            while buckets[topic]:
                record=buckets[topic].popleft()
                if domains[record['domain']]>=config['max_per_domain']:continue
                selected.append(record);domains[record['domain']]+=1;progressed=True
                break
            if len(selected)>=config['target_records']:break
        if not progressed:break
    metrics=dict(raw_count=len(raw),invalid_metadata=rejected,unique_urls=len(by_url),duplicate_urls_removed=len(raw)-rejected-len(by_url),
                 sample_count=len(selected),target=config['target_records'],shortfall=max(0,config['target_records']-len(selected)),
                 source_domains=len({r['domain'] for r in selected}),same_title_clusters={k:v for k,v in Counter(r['title_cluster'] for r in selected).items() if v>1},
                 by_domain=dict(Counter(r['domain'] for r in selected)),by_topic=dict(Counter(r['discovered_by'][0]['topic'] for r in selected)),
                 algorithm_relevant=sum(r['pollution_assessment']['marine_pollution_relevant'] for r in selected),
                 algorithm_incident_candidates=sum(r['pollution_assessment']['record_kind']=='incident_candidate' for r in selected),
                 confirmed_incidents=0,full_texts_checked=0,publication_dates_known=sum(r['publication_date'] is not None for r in selected),
                 human_reviewed=0,precision=None,notion_writes=0)
    return selected,metrics


def safe(value):
    value='' if value is None else str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value


def write_pilot(raw,statuses,config,output):
    records,metrics=build_sample(raw,config)
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    if any(path.iterdir()):raise ValueError('Pilot output must be new or empty')
    for name,data in [('news_sample.json',records),('raw_news_metadata.json',raw),('collection_status.json',statuses),('pilot_config.json',config),('quality_summary.json',metrics)]:
        (path/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    fields=['id','title','url','domain','language','publisher_country','publication_date','gdelt_seen_at','content_scope','algorithm_relevant','algorithm_record_kind','pollution_categories','missing_information']+REVIEW_FIELDS
    with (path/'quality_review.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for record in records:
            row={key:record.get(key) for key in fields}
            a=record['pollution_assessment']
            row.update(algorithm_relevant=a['marine_pollution_relevant'],algorithm_record_kind=a['record_kind'],pollution_categories='; '.join(a['pollution_categories']),
                       missing_information='Article body, incident date/location, original evidence, publisher credibility not verified; publication date may be unknown')
            writer.writerow({key:safe(value) for key,value in row.items()})
    display=[dict(r,date=r['publication_date'] or r['gdelt_seen_at'],score=None,matched_groups=r['pollution_assessment']['pollution_categories'],supporting_excerpt=r['text'] or 'Discovery title only; open source URL and review. GDELT date is first-seen time, not publication/event date.') for r in records]
    write_dashboard(display,path)
    # Replace academic-oriented labels in this metadata-only pilot view.
    dashboard=(path/'dashboard.html').read_text().replace('Yayın tarihi','RSS yayın tarihi / GDELT ilk görülme zamanı')
    (path/'dashboard.html').write_text(dashboard,encoding='utf-8')
    lines=['# MAPDIS haber kalite pilotu','',f"Hedef: {metrics['target']}; örnekleme alınan gerçek haber bağlantısı: {len(records)}; eksik: {metrics['shortfall']}.",'',
           'Bu örneklem sorgu sonuçlarından konu sırasıyla dengelenir; algoritmanın ilgili bulmadığı adaylar da korunur. Sıra/sorgu/kaynak seçimi nedeniyle rastgele veya tüm haber evrenini temsil eden bir örneklem değildir.','',
           '## Kontrol kapsamı','', 'GDELT keşif başlıkları veya izinli RSS özetleri ve URL metadatası kullanılır. Yayıncı sayfaları/tam metinler, kaynak doğruluğu ve olay gerçekliği kontrol edilmiş sayılmaz. GDELT seendate yayın veya olay tarihi değildir; sourcecountry olay ülkesi değildir.','',
           'quality_review.csv dosyasındaki insan değerlendirme alanları bilerek boştur. Otomatik sinyaller kalite kararı veya ölçülmüş başarı oranı değildir.','',
           '## İnceleme ölçütleri','',
           '- human_relevance: yes / no / uncertain — gerçekten deniz/kıyı kirliliğiyle ilgili mi?',
           '- human_incident: yes / no / uncertain — somut bir olay mı, araştırma/genel bilgi mi?',
           '- human_source_quality: reliable / questionable / unknown — yayıncı, yazar, atıf ve bağımsız doğrulama nasıl?',
           '- human_evidence_sufficient: yes / no / uncertain — olayın tarihi, yeri ve iddiası kaynakta destekleniyor mu?',
           '- decision: accept / reject / review — Notion aktarım onayı değildir.',
           '- reviewer_notes: gerekçe, kullanılan alıntı ve bağımsız kaynak URL’leri.','',
           'Her kaydı asıl kaynakta kontrol edin. Paywall/robots/erişim engelini aşmayın. Eksik kanıtta review/uncertain kullanın; sayıyı tamamlamak için tahmin üretmeyin.','',
           '## Ölçek büyütme','', 'Bu pilot incelenmeden 1.000–10.000 kayıt toplamaya veya Notion yazımına geçilmez. Önce etiketli örneklemle ilgili haber oranı, olay oranı, kopyalar, kaynak güvenilirliği ve eksik kanıtlar ölçülür. Tekrar değerlendirme, karantinaya alma ve oran sınırlı onaylı aktarım ayrı aşamadır. Notion hâlâ dry-run.','',
           '## Otomatik sayımlar (insan kalite kararı değil)','', '```json',json.dumps(metrics,ensure_ascii=False,indent=2),'```','', '## Kaynak bağlantıları','']
    lines += [f"- [{r['id']}] {r['title']} — <{r['url']}>" for r in records]
    if any(s['status']=='failed' for s in statuses):lines+=['','Bazı sorgular engellendi/başarısız. collection_status.json dosyasındaki hata kökenini inceleyin; sıfır/eksik veri başarı değildir.']
    (path/'quality_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return metrics


def evaluate_reviews(path):
    """Evaluate explicit human labels, with an actual reviewed denominator."""
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        required={'id','algorithm_relevant','human_relevance','human_incident','human_source_quality','human_evidence_sufficient','decision'}
        if not required<=set(reader.fieldnames or []):raise ValueError('Expected pilot review CSV')
        rows=list(reader)
    ids=[r['id'] for r in rows]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate review IDs')
    allowed={'human_relevance':{'yes','no','uncertain',''},'human_incident':{'yes','no','uncertain',''},'human_source_quality':{'reliable','questionable','unknown',''},'human_evidence_sufficient':{'yes','no','uncertain',''},'decision':{'accept','reject','review',''}}
    for row in rows:
        for key,values in allowed.items():
            row[key]=row[key].strip().lower()
            if row[key] not in values:raise ValueError(f'Invalid review option: {key}')
    reviewed=[r for r in rows if r['human_relevance'].strip().lower() in {'yes','no'}]
    predicted=[r for r in reviewed if r['algorithm_relevant'].lower()=='true']
    return dict(total=len(rows),human_relevance_reviewed=len(reviewed),unreviewed_or_uncertain=len(rows)-len(reviewed),
                relevant_count=sum(r['human_relevance'].lower()=='yes' for r in reviewed),
                relevant_fraction=sum(r['human_relevance'].lower()=='yes' for r in reviewed)/len(reviewed) if reviewed else None,
                algorithm_precision_on_reviewed_predictions=sum(r['human_relevance'].lower()=='yes' for r in predicted)/len(predicted) if predicted else None,
                decision_counts=dict(Counter(r['decision'].strip().lower() or 'unreviewed' for r in rows)),
                notion_writes=0,note='Review labels only; no Notion write or automatic factual verification')
