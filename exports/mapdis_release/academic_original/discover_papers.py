import json
from pathlib import Path
from mapdis_research.http import Client
from mapdis_research.config import load_config
from mapdis_research.sources import abstract_from_index
c=load_config('config/sample.json')
client=Client(c)
p=Path('output/sentinel1_verified'); p.mkdir(exist_ok=True)
r=client.get('https://api.openalex.org/works',params={'search':'oil spill Sentinel-1 detection','filter':'type:article,from_publication_date:'+c['date_from'],'per-page':50})
data=r.json(); (p/'openalex_discovery.json').write_text(json.dumps(data,indent=2))
for i,w in enumerate(data['results']):
 print(i,w['doi'],w['title'])
 print(abstract_from_index(w.get('abstract_inverted_index'))[:450])
