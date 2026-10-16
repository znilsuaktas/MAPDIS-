"""Explainable triage of pollution relevance; never verifies an incident."""
import re
from .matching import contains

TAXONOMY = {
    'oil': ['oil spill','oil spills','oil slick','petroleum','fuel spill','fuel oil','crude oil','diesel','bunker oil','hydrocarbon','petrol sızıntısı','petrol döküntüsü','akaryakıt sızıntısı'],
    'plastic': ['plastic pollution','plastic waste','plastic debris','marine debris','microplastic','microplastics','macroplastic','nurdle','nurdles','plastic pellets','plastik atık','mikroplastik','plastik kirliliği'],
    'mucilage': ['mucilage','sea snot','müsilaj','deniz salyası'],
    'wastewater': ['sewage','wastewater','untreated water','effluent','sewer overflow','kanalizasyon','atık su','atıksu','arıtılmamış'],
    'chemical': ['chemical spill','toxic waste','chemical waste','industrial discharge','heavy metals','pesticides','chemical contamination','kimyasal sızıntı','zehirli atık','sanayi atıkları','ağır metal'],
    'bloom': ['algal bloom','algae bloom','red tide','eutrophication','harmful algae','alg patlaması','kırmızı gelgit','ötrofikasyon'],
    'unclassified': ['pollution','polluted','contamination','contaminated','fish kill','fish deaths','dead fish','black slick','kirlilik','kirliliği','kirlenen','balık ölümleri','balıklar öldü'],
}
MARINE = ['sea','ocean','marine','coast','coastal','beach','shore','harbour','harbor','seawater','bay','estuary','lagoon','Mediterranean','Marmara','Black Sea','Aegean','deniz','denizi','denize','denizde','denizden','sahil','sahile','sahilde','kıyı','kıyıya','kıyıda','körfez','liman','Karadeniz','Akdeniz','Ege']
EVENTS = ['spill','spilled','leaked','discharged','washed ashore','caught fire','sank','grounded','reported','detected','dead fish','fish kill','balıklar öldü','balık ölümleri','sızdı','döküldü','boşaltıldı','vurmuş','vurdu','kirlendi','tespit edildi','sızıntı','discharge','dumped','ulaştı','dökülen']
UNCERTAIN = ['may cause','could cause','might cause','potential risk','risk of','hypothetical','simulated','simulation','modelled','modeled','olasılığı','riski','simülasyon','senaryo']
NEGATIVE = ['no pollution','no contamination','no oil spill','not polluted','not contaminated','kirlilik bulunmadı','kirlilik tespit edilmedi','sızıntı tespit edilmedi','kirlilik yok']


def assess(record):
    text = record.get('title','') + '\n' + record.get('text','')
    categories = {name:[term for term in terms if contains(text,term)] for name,terms in TAXONOMY.items()}
    categories = {name:terms for name,terms in categories.items() if terms}
    marine = [term for term in MARINE if contains(text,term)]
    events = [term for term in EVENTS if contains(text,term)]
    uncertainty = [term for term in UNCERTAIN+NEGATIVE if contains(text,term)]
    nonmarine_focus = any(contains(text,t) for t in ['air pollution','hava kirliliği','noise pollution','gürültü kirliliği']) and set(categories) <= {'unclassified'}
    relevant = bool(categories and marine) and not nonmarine_focus
    academic = record.get('source') in {'openalex','crossref','openalex + crossref'} or bool(record.get('doi')) or record.get('publication_type') in {'article','journal-article','proceedings-article','book-chapter'}
    if academic:
        kind = 'academic_research'
    elif relevant and events and not uncertainty:
        kind = 'incident_candidate'
    else:
        kind = 'background_or_ambiguous' if relevant else 'unrelated_or_insufficient_context'
    terms = sum(categories.values(),[]) + marine + events
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    excerpts = [s for s in sentences if s and any(contains(s,term) for term in terms)]
    return {'marine_pollution_relevant': relevant, 'record_kind':kind,
            'pollution_categories':list(categories), 'pollution_signals':categories,
            'marine_context':marine, 'event_signals':events, 'uncertainty_signals':uncertainty,
            'supporting_excerpts':excerpts[:4], 'verified_incident':False,
            'explanation':'Rule-based source-text triage, not general language understanding or factual verification. Satellite terms are not required.'}
