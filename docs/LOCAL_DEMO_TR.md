# MAPDIS-AI: Windows / VS Code yerel kurulum ve sunum

## 1. Projeyi bilgisayarına al

Git for Windows, Python 3.10+ ve VS Code kurulu olmalı. VS Code'da Microsoft Python eklentisini yükle. PowerShell:

```powershell
cd $env:USERPROFILE\Documents
git clone --branch feature/mapdis-scraper https://github.com/znilsuaktas/MAPDIS-.git
cd MAPDIS-
code .
```

Daha önce klonladıysan proje klasöründe `git status` ile kendi değişikliklerini kontrol et. Temizse `git pull --ff-only origin feature/mapdis-scraper` kullan; yerel dosyalarını silme/resetleme. Bu sohbet bulut makinesinde çalışır; bilgisayarına fiziksel kurulum bu adımlarla yapılır.

## 2. Kurulum ve test

VS Code → Terminal → New Terminal → PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

VS Code komut paletinde **Python: Select Interpreter** → `.venv\Scripts\python.exe` seç. Sanal ortamı aktive etmen şart değil; komutlar doğrudan doğru Python'u çağırıyor. İsteğe bağlı aynı kurulum/test adımları `./scripts/Setup-Local.ps1` içinde bulunur. PowerShell script politikan çalıştırmayı engellerse yukarıdaki doğrudan komutları kullan; politika değişikliği zorunlu değildir.

## 3. Araştırma profilleri

```powershell
.\.venv\Scripts\python.exe -m mapdis_research profiles
```

| Profil | Benzersiz eşleşme ifadesi | Amaç |
|---|---:|---|
| oil_spill | 51 | Petrol, tanker, SAR ve uydu tespiti |
| plastic | 52 | Deniz plastiği, mikroplastik, nurdle, optik uydu |
| mucilage | 56 | Müsilaj, alg patlaması, Marmara ve uzaktan algılama |
| all | 150 | Birleşik araştırma |
| marine_pollution | 93 | Uydu şartı olmadan geniş kirlilik bağlamı |

Varsayılan gelişmiş profil `marine_pollution` oldu. [Uydu şartı olmadan kirlilik tespiti](POLLUTION_RELEVANCE_TR.md) haber/RSS durumu ve sınırlamaları açıklar.

Profillerde ortak sensör/yöntem kelimeleri bulunur; sayılar birbirine eklenmez. Türkçe/İngilizce varyantlar `config/advanced.json` dosyasında açıkça listelenir. Arama sorguları (`queries`) ile yerel eşleşme sözlüğü (`keywords`) ayrıdır. Her kelimenin ayrı ayrı için API çağrısı yapılmaz. Bu sözlük bilimsel kapsama garantisi veya otomatik çeviri değildir.

Önce ağ çağrısı yapmadan tarama sınırını göster:

```powershell
.\.venv\Scripts\python.exe -m mapdis_research plan --profile oil_spill --max-queries 2 --pages 2
```

İki kaynak × iki sorgu × iki sayfa = en fazla sekiz API çağrısı, en fazla 80 ham kayıt (sayfa başı 10). Gerçek sayı daha düşük olabilir. Tarih filtreleri, anahtar kelimeler, negatif ifadeler ve zorunlu konu grupları düzenlenebilir. Örneğin yalnız Sentinel kelimesi içeren heyelan makalesi petrol grubunu karşılamadığı için elenir. Kelimeler kelime sınırlarıyla eşleşir; `oil`, `soil` içinde eşleşmez. Tire ve Türkçe karakter varyantları normalleştirilir.

## 4. Hocaya canlı tarama göster

```powershell
$demoOutput = "output/demo_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff")
.\.venv\Scripts\python.exe -m mapdis_research run --config config/advanced.json --profile oil_spill --max-queries 2 --pages 2 --output $demoOutput
Get-Content "$demoOutput/summary.json"
Start-Process "$demoOutput/dashboard.html"
```

Alternatif yerel başlatıcı:

```powershell
.\scripts\Run-Local.ps1 -Profile plastic -MaxQueries 2 -Pages 1 -OpenDashboard
```

VS Code F5 menüsünde **MAPDIS: yerel petrol taraması** yapılandırması da vardır. Her çalışma yeni bir klasör seçer; dolu çıktı klasörü kullanılırsa program hata vererek mevcut dosyaları korur. İnternet erişimi ve API hizmetlerinin çalışması gerekir; LLM/Notion anahtarı gerekmez. Çok büyük taramalardan önce `plan` ile istek üst sınırını kontrol et.

`dashboard.html` dosyasını tarayıcıda açıp Sentinel, Marmara veya plastik gibi ifadelerle sonuçlar içinde ara. Dosya kendi kendine yeterlidir; sunucu, harici JavaScript/CDN veya web hesabı gerektirmez. Kaynak bağlantılarına tıklamak internet gerektirir. Bu ekran araştırma sonuçlarını gösterir, Notion'a yazmaz.

## 5. Çıktıları anlat

- `results.csv` / `results.json`: deduplikasyon, filtreleme ve puanlama sonrası sonuçlar. Eski alanlara ek olarak yazar, dergi, yayın türü, konu grupları, keşif sorguları ve puan bileşenleri bulunur.
- `report.md`: kaynak bağlantılı alıntılar; bilimsel iddiaların bağımsız doğrulandığı anlamına gelmez.
- `dashboard.html`: yerel, aranabilir sonuç tablosu.
- `raw_records.json`: gerçekten alınan ham kayıtlar; yeniden işleme girdisi.
- `effective_config.json`: o çalışmada kullanılan araştırma ayarları.
- `search_log.json`: sorgu/sayfa bazında başarı veya hata; HTTP hata kodu mevcutsa kaydedilir.
- `summary.json`: ham/son kayıt sayıları, grup/kaynak dağılımı, özeti eksik kayıtlar, başarısız sayfalar. Eleme ve kopya sayısı birlikte raporlanır; iki ayrı sayı gibi sunulmaz.
- `run.json`: kaynak bazında sonuç; kısmi hatalar başarı olarak gizlenmez.

Aynı DOI/URL birden çok sorguda bulunduğunda tek sonuç kalır; hangi kaynak ve sorgulardan geldiği korunur. Çok sayıda eş anlamlı kelime puanı yapay olarak düşürmesin diye gelişmiş profillerde eşleşme puanı yapılandırılabilir doygunluk hedefi kullanır. Kalite ağırlığı bir sezgiseldir, gerçeklik onayı değildir. 403/429 sonrasında kaynağa tekrar tekrar istek atılmaz; eldeki kayıtlar korunur ve çıkış kodu 1 olur.

## 6. İnternetsiz yeniden işleme göster

Önce gerçek bir canlı çalışma yap. Ardından aynı ham veriyi kullan:

```powershell
$replayOutput = "output/replay_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff")
.\.venv\Scripts\python.exe -m mapdis_research replay --input "$demoOutput/raw_records.json" --config "$demoOutput/effective_config.json" --output $replayOutput
Start-Process "$replayOutput/dashboard.html"
```

`replay` yeni veri aramaz; mevcut gerçek ham kayıtları yeniden filtreleyip CSV/JSON/rapor üretir. Örneğin internet kesilirse hocaya kayıtlı veriden rapor üretimini gösterebilirsin. Bunu canlı veri toplama diye sunma.

İlk canlı çalışma öncesinde de GitHub paketindeki gerçek akademik kayıtlarla internetsiz deneme yapabilirsin:

```powershell
.\.venv\Scripts\python.exe -m mapdis_research replay --input exports/mapdis_release/academic_original/results.json --config config/advanced.json --profile oil_spill
```

Bu komut kaydedilmiş akademik sonuçları işler; yeni veri toplamaz.

## 7. Gerçek olaylar ve Notion ayrı tutulur

`incidents --config config/incidents.json --output <yeni-klasör>` komutu, gözden geçirilmiş olay manifestinin kaynaklarını yeniden kontrol eder. Akademik keşif sonuçları otomatik olarak olay kayıtlarına çevrilmez. Hazır 5 olaylık doğrulanmış paket `exports/mapdis_release/` altında korunur; yeni canlı çalışmalar bu paketi değiştirmez. Notion'un 16 alanı değişmedi: Estimated Area Rich Text, Longitude adı/türü teyit bekliyor. Notion senkronizasyonu dry-run; yazma komutları kapalıdır.

## Kontrol sınırları

Python testleri ve üç profilin sınırlı canlı API denemeleri bulut Linux ortamında yürütülür. Bu ortamda Windows/PowerShell çalıştırıcısı yoktur; `.ps1` dosyalarının gerçek Windows çalışması burada doğrulanamaz. Yerel kurulumda bir hata alırsan tam komutu ve anahtar içermeyen hata metnini paylaş. Eski doğrulanmış ZIP/CSV dosyaları bu geliştirmede yeniden yazılmaz.

OpenAlex çok sayfalı taramasında, anahtarsız desteklenen basic `page` parametresi kullanılır. Cursor ile ikinci sayfa API anahtarı isteyebildiği için o yöntem kullanılmaz. Crossref sayfalarında ise resmi cursor parametresi kullanılır. Kimlik doğrulama ve korumalar aşılmaz.
