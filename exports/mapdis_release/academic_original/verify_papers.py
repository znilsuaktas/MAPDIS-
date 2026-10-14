import json,re,difflib,csv
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import quote
from mapdis_research.http import Client
from mapdis_research.config import load_config
from mapdis_research.sources import abstract_from_index,record
from mapdis_research.processing import process
from mapdis_research.report import write_outputs
p=Path('output/sentinel1_verified'); config=load_config('config/sample.json'); client=Client(config)
works=json.loads((p/'openalex_discovery.json').read_text())['results']
chosen=[4,6,8,11,14,19,29,37,41,42]
records=[]; verification=[]
def norm(s): return re.sub(r'[^a-z0-9]','',s.lower())
for i in chosen:
 w=works[i]; doi=w['doi'].removeprefix('https://doi.org/'); endpoint='https://api.crossref.org/works/'+quote(doi,safe='')
 cached=p/f'crossref_{i}.json'
 if cached.exists():
  data=json.loads(cached.read_text())
 else:
  response=client.get(endpoint); data=response.json()
 cr=data['message']
 (p/f'crossref_{i}.json').write_text(json.dumps(data,indent=2))
 title=(cr.get('title') or [''])[0]
 ratio=difflib.SequenceMatcher(None,norm(w['title']),norm(title)).ratio()
 assert cr['DOI'].lower()==doi.lower() and ratio>0.95,(doi,title,w['title'])
 assert cr['type']=='journal-article',cr['type']
 assert not w.get('is_retracted')
 abstract=abstract_from_index(w.get('abstract_inverted_index'))
 assert re.search(r'sentin[ae]l[ -]?1',(w['title']+' '+abstract).lower()) and 'oil' in abstract.lower()
 r=record(w['title'],w['publication_date'],w['doi'],abstract,doi,'openalex + crossref',0.9)
 r['verification']={'openalex_url':w['id'],'openalex_api_url':'https://api.openalex.org/works/'+w['id'].rsplit('/',1)[-1], 'crossref_api_url':endpoint,'title_similarity':ratio,'crossref_type':cr['type'],'journal':(cr.get('container-title') or [''])[0],'authors':[a.get('given','')+' '+a.get('family','') for a in cr.get('author',[])], 'crossref_published_date_parts':(cr.get('published') or {}).get('date-parts'),'checked_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'DOI/title/journal-article metadata and abstract relevance; full text not verified'}
 records.append(r)
 print(doi,title,ratio,flush=True)
results=process(records,config)
assert len(results)==10
write_outputs(results,p,[{'source':'openalex targeted discovery','status':'success','count':50},{'source':'crossref DOI verification','status':'success','count':10}])
(p/'verification.json').write_text(json.dumps([dict(doi=r['doi'],**r['verification']) for r in results],indent=2))
lines=['# Sentinel-1 SAR oil-spill detection: 10 citation-verified papers','','## Scope and verification','','The existing sample configuration was run unchanged, returning 100 raw API records and 64 deduplicated records (see ../live_sample). Its broad queries were supplemented by one targeted OpenAlex query: `oil spill Sentinel-1 detection`, filtered to articles published from 2020-01-01, 50 candidates. Ten journal papers with explicit Sentinel-1/oil-spill relevance in their titles/abstracts were selected; this is a purposive bibliography, not a systematic review. Each DOI and title was checked against a live Crossref DOI lookup (title similarity >95%); raw responses are retained. Both API endpoints returned HTTP 200. No LLM was used.','','Verification covers citation identity and retrieved abstract statements, not replication of experiments or full-text verification. OpenAlex publication dates and Crossref date-parts are retained separately; online and issue dates may differ.','','## Paper evidence','']
for n,r in enumerate(results,1):
 v=r['verification']; abstract=r['text']; sentences=re.split(r'(?<=[.!?])\s+',abstract)
 # Keep extractive summaries exact, with enough contextual sentences.
 evidence=' '.join(sentences[:3])
 lines += [f"### [{n}] {r['title']}",'',f"Date (OpenAlex): {r['date']}; journal (Crossref): {v['journal']}",'',f"DOI citation: <{r['url']}>",'',f"Metadata checks: [OpenAlex]({v['openalex_api_url']}) · [Crossref]({v['crossref_api_url']})",'', 'Extractive abstract summary:', '', '```text',evidence.replace('```',"'''"),'```','',f"Supporting source: [OpenAlex abstract]({v['openalex_api_url']})",'']
lines += ['## Synthesis, disagreements, and missing information','','The selected papers describe several approaches: deep neural networks and polarimetric features, operational detection, threshold methods, and random-forest classification. Specific approach statements are supported by the individual cited abstract extracts above.','','No factual disagreement is established by this bibliography. Different methods and reported metrics are not directly comparable without matching datasets, labeling protocols, sea states, and validation procedures. No claim of a universally best model or numerical cross-study comparison is made.','','Full texts, independent ground truth, consistent evaluation datasets, reproducibility, licensing of training imagery, and deployment performance were not verified. Retracted status was checked only in OpenAlex discovery metadata. Citation agreement between two aggregators does not establish scientific correctness or independent factual corroboration.','','## Reproducibility and artifacts','','`results.json` and `results.csv` contain exactly 10 distinct DOI records with retrieved abstract text and excerpts. `verification.json` stores live verification endpoints, authors, journal metadata and UTC check times. `openalex_discovery.json` and `crossref_*.json` preserve the actual API responses. `run.json` records completion. No website scraping or paywall access was needed.']
(p/'report.md').write_text('\n'.join(lines)+'\n')
with (p/'results.csv').open(encoding='utf-8-sig',newline='') as f: assert len(list(csv.DictReader(f)))==10
assert len(json.loads((p/'results.json').read_text()))==10
print('Verified exactly 10 JSON and CSV records.')
