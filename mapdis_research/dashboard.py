"""Self-contained, offline, searchable HTML report (no server/dependency)."""
import html
from pathlib import Path
from urllib.parse import urlsplit


def write_dashboard(records, output):
    esc = lambda value: html.escape(str(value or ''), quote=True)
    rows = []
    for r in records:
        url = r.get('url', '')
        link = f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Kaynak</a>' if urlsplit(url).scheme in {'http', 'https'} else 'Geçersiz URL'
        rows.append('<tr>'+''.join(f'<td>{value}</td>' for value in [esc(r.get('title')), esc(r.get('date') or 'Bilinmiyor'), esc(r.get('source')), esc(r.get('score')), esc(r.get('pollution_assessment', {}).get('record_kind', '') + ' | ' + ', '.join(r.get('pollution_assessment', {}).get('pollution_categories', [])) + ' | ' + ', '.join(r.get('matched_groups', []))), esc(r.get('supporting_excerpt')), link])+'</tr>')
    body = '''<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAPDIS araştırma sonuçları</title><style>body{font-family:system-ui;margin:2rem;background:#f5f8fc;color:#172b42}input{padding:.7rem;width:70%;margin:1rem 0}table{border-collapse:collapse;width:100%;background:white}th,td{padding:.7rem;text-align:left;border-bottom:1px solid #ddd;vertical-align:top}th{background:#173a56;color:white}td:nth-child(6){max-width:32rem}a{color:#00669c}</style>
<h1>MAPDIS-AI Araştırma Sonuçları</h1><p>Kaynak alıntılarıdır; bağımsız olarak doğrulanmış olay veya hazır eğitim verisi değildir.</p>
<label for="search">Başlık, tarih, kaynak veya konu içinde ara:</label><br><input id="search" type="search" placeholder="Örnek: Sentinel, Marmara, plastic"><p id="count"></p>
<table><thead><tr><th>Başlık</th><th>Yayın tarihi</th><th>Kaynak</th><th>Puan</th><th>Kayıt türü / Kirlilik / Konular</th><th>Destekleyici alıntı</th><th>Bağlantı</th></tr></thead><tbody>'''
    body += ''.join(rows)
    body += '''</tbody></table><script>const rows=Array.from(document.querySelectorAll('tbody tr'));const input=document.getElementById('search');function filter(){let count=0;const query=input.value.toLocaleLowerCase('tr');for(const row of rows){row.hidden=!row.textContent.toLocaleLowerCase('tr').includes(query);if(!row.hidden)count++;}document.getElementById('count').textContent=count+' / '+rows.length+' sonuç';}input.addEventListener('input',filter);filter();</script></html>'''
    Path(output, 'dashboard.html').write_text(body, encoding='utf-8')
