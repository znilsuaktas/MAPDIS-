# Önce 50–100 haber: kalite pilotu

Hocanın önerisi iki ayrı aşamadır: önce küçük, incelenebilir bir haber örneklemi; sonra sonuçlara göre kontrollü ölçek büyütme. 1.000–10.000 sonuç toplamayı ya da Notion'a yazmayı bu pilot başlatmaz.

## Yerelde topla

Proje klasöründe PowerShell:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pytest -q
$pilot = "output/news_pilot_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff")
.\.venv\Scripts\python.exe -m mapdis_research news-pilot --output $pilot
Start-Process "$pilot/dashboard.html"
```

Ayarlar `config/news_pilot.json` içindedir: hedef 100 haber bağlantısı, son 60 gün, konu başına en çok 100 arama sonucu, yayıncı alan adı başına en çok 15 kayıt, en az 5 saniye istek aralığı. `target_records` 50–100 arasında değiştirilebilir. GDELT DOC API haber keşif metadatası kullanılır; OpenAlex/Crossref makaleleri sayıyı tamamlamak için eklenmez.

Varsayılan sorgular petrol, plastik, atık su ve müsilaj/kimyasal/alg olaylarını arar. Uydu veya Sentinel şartı yoktur. Sonuçlar konu sırasıyla dengelenerek seçilir; bu rastgele/temsil edici örneklem iddiası değildir. İlgisiz görünen arama sonuçları da pilotta tutulur; yalnız olumlu tahminleri seçip başarıyı yapay yükseltmeyiz. Kanonik URL kopyaları kaldırılır, farklı sitelerde aynı başlıklar küme olarak raporlanır.

## Ne toplanır, ne doğrulanmaz?

Başlık, asıl haber URL'si, yayıncı alan adı/dili, GDELT ilk-görülme zamanı ve keşif sorgusu kaydedilir. GDELT tam makale metni veya güvenilir olay teyidi sağlamaz. `seendate` yayın/olay tarihi değildir; `sourcecountry` olay ülkesi değildir. Kaynak/olay ülkesi, olay tarihi, alan ve koordinatlar bilinmiyorsa null kalır. Yayıncı haber sayfalarının erişimi, kullanım koşulları ve kaynak kalitesi otomatik doğrulanmış sayılmaz; sayfalar topluca indirilmez.

Bu nedenle ilk sürümün haber kalitesini gerçekten ölçmek için asıl URL'leri insan incelemelidir. Sayfa erişilemiyorsa, paywall/robots engeli varsa aşmayın; review/uncertain kullanın. Haber URL'lerinin yalnız sözdizimsel olarak geçerli olması erişilebilir veya güvenilir olduklarını kanıtlamaz.

## İncele ve etiketle

1. `quality_review.csv` dosyasını Excel'de **Veri → Metin/CSV'den**, UTF-8 olarak aç.
2. Her haberin asıl kaynağını açıp olayın yerini, zamanını, kirlilik iddiasını ve kaynak dayanağını kontrol et.
3. `human_relevance`: `yes`, `no`, `uncertain` — gerçekten deniz/kıyı kirliliği mi?
4. `human_incident`: `yes`, `no`, `uncertain` — somut olay mı, genel araştırma/risk yazısı mı?
5. `human_source_quality`: `reliable`, `questionable`, `unknown` — kaynak, yazar, atıf ve bağımsız teyit yeterli mi?
6. `human_evidence_sufficient`: `yes`, `no`, `uncertain` — iddialar kaynakta destekleniyor mu?
7. `decision`: `accept`, `reject`, `review`. Notion'a yazma onayı değildir.
8. `reviewer_notes`: karar gerekçesi, alıntı ve ek teyit URL'lerini yaz. Kimlik (`id`) sütununu değiştirme.
9. İncelenen CSV'yi ayrı bir dosya olarak kaydet; orijinali koru.

```powershell
.\.venv\Scripts\python.exe -m mapdis_research review-pilot --input "$pilot/quality_review_incelendi.csv"
```

Değerlendirme, yalnız açık yes/no insan etiketleri üzerinde oran hesaplar. Boş veya uncertain etiketler paydadan ayrılır; hiç etiket yoksa başarı oranı null'dır. Otomatik ilgili/olay adayı sayısı insan doğruluğu veya kaynak güvenilirliği değildir.

## Çıktılar

- `quality_review.csv`: inceleme tablosu; insan karar alanları başlangıçta boş.
- `news_sample.json`: gerçek keşif kayıtları; bilinmeyen alanlar null.
- `raw_news_metadata.json`: alınmış API sonuçları ve sorgu bilgisi.
- `collection_status.json`: sorgu başarısı veya erişim hatası ve kökeni.
- `quality_summary.json`: adetler, kopyalar, kaynak/konu dağılımı, eksikler; etiketsiz doğruluk null.
- `quality_report.md`: inceleme ölçütleri, sınırlamalar ve her kaydın kaynak URL'si.
- `dashboard.html`: yerel inceleme ekranı. Gösterilen zamanın GDELT ilk görülme zamanı olduğu açıkça belirtilir.

## Ölçek büyütmeden önce

Etiketli pilotta ilgili haber oranını, somut olay oranını, aynı olayın tekrarlarını, kaynak çeşitliliğini ve eksik kanıtları hocanla değerlendirin. Kabul ölçütlerini sonuçlara göre açıkça belirleyin; ölçülmemiş bir başarı yüzdesi iddia etmeyin. 1.000–10.000 kayıt aşaması API sınırları, olay düzeyinde deduplikasyon, karantina, tekrar kontrol ve açıkça onaylı Notion aktarımı için ayrı geliştirme gerektirir. Mevcut pilot 100 ile sınırlıdır; Notion yazımı kapalıdır.

## Bulut denemesinin gerçek sonucu (2026-10-16)

GDELT API'si bu çalışan bulut makinesinde `Tunnel connection failed: 403 Forbidden` ile engellendi. Hata HTTPS tüneli kurulurken Codex cloud proxy'den geliyor; hedef API'nin verdiği bir HTTP 403 olduğuna dair kanıt yok. Sonuç **0/100 haber**; 100 gerçek haber toplanmış veya kalitesi doğrulanmış değildir. Hata çıktısı `output/news_pilot_attempt_20261016/` altında; bu dizin Git'e eklenmez.

`api.gdeltproject.org` ve dokümantasyon için `blog.gdeltproject.org` alan adları mevcut ağ kuralları korunarak ortam taslağına eklendi. Ortam ayarlarında bunları inceleyip kaydetmek/yayınlamak ve erişimi yeniden test etmek gerekir. Taslak kaydetmek tek başına çalışan makineyi güncellediğini kanıtlamaz. Yerel bilgisayarda API erişimi de ayrıca test edilmelidir. API erişimi açılmadan sayıyı akademik makale veya uydurma haberlerle tamamlamıyoruz.

## Windows'ta HTTPError görülürse

Önce taramayı tekrar tekrar başlatmadan mevcut hata dosyasını oku:

```powershell
Get-ChildItem .\output -Filter collection_status.json -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }
```

`http_status` 429 ise API hız sınırına ulaşıldı; varsa `retry_after` süresini bekle. 403 tek başına Codex bulut proxy'sini göstermez: kullanıcı Windows'ta çalışıyorsa API veya yerel ağ güvenlik katmanı olabilir. Proxy CONNECT reddi ayrı `proxy_CONNECT_403` olarak kaydedilir. 401 erişim/kimlik doğrulaması, 5xx hizmet erişilebilirliği için ayrıca incelenmelidir. Kod artık terminalde HTTP kodunu ve varsa bekleme başlığını gösterir. API anahtarı, `.env` içeriği veya tüm ortam değişkenlerini paylaşmayın.

## Tekrarlayan GDELT 429: bağımsız RSS seçeneği

`--provider rss` GDELT'e hiç istek göndermez. Yapılandırması `config/news_rss_pilot.json` dosyasıdır. Dört Guardian çevre feed'i **aday URL** olarak listelenir; bu bulut makinesinde robots/koşul erişimi engellendiği için canlı çalıştıkları ve yeniden kullanım koşulları doğrulanmış değildir. Kaynaklar bu yüzden varsayılan olarak kapalıdır. Bu seçenek, GDELT kısıtlamasını başka IP/proxy ile aşmaya çalışmaz; bağımsız sağlayıcıdır.

Yerel erişim ve kullanım koşulları kontrol edilip izinli olduğu doğrulanan feed için `enabled` ve `terms_reviewed` true yapılabilir. robots izni ayrıca kontrol edilir. Ardından:

```powershell
.\.venv\Scripts\python.exe -m mapdis_research news-pilot --provider rss
```

İncelenmemiş/kapalı kaynaklar okunmaz; eksik hedef yine başarı sayılmaz. RSS akışları sonlu olduğundan 50–100 kayıt garanti edilmez. Aynı yayıncının farklı konu feed'leri bağımsız yayıncı çeşitliliği değildir; alternatif örnekte `max_per_domain=100` tek yayıncı pilotunu mümkün kılar, kaliteyi veya temsil gücünü doğrulamaz.

RSS'de feed'in yayın tarihi GDELT ilk-görülme zamanından ayrı tutulur; yayın tarihi olay tarihi değildir. `lookback_days` dışındaki bilinen eski tarihler elenir, bilinmeyen tarihler null kalır. Yayıncı sayfaları otomatik indirilmez. Pilot, tam metin teyidi ve Notion aktarımı yapmaz.

## Windows UnicodeDecodeError sonrası haberleri yeniden indirmeden onarma

2026-10-17'de pilot raporunda bir Windows kodlama hatası yeniden üretildi: `dashboard.html` UTF-8 yazıldığı halde kodlama belirtmeden okunuyordu. Windows varsayılanı cp1254 olduğunda bazı haber başlıkları `UnicodeDecodeError` üretebiliyordu. Okuma artık açıkça UTF-8 kullanır; karakterleri silme/değiştirme veya `errors=ignore` uygulanmaz. Bu, Türkçe dışındaki haber başlıklarının da korunmasını sağlar. Windows cp1254 varsayılanını taklit eden regresyon testi eklendi; gerçek Windows çalışması kullanıcı makinesinde ayrıca kontrol edilir.

Bu adım ham JSON/CSV üretiminden sonra gerçekleştiği için hata alınmış olsa da veriler kaydedilmiş olabilir. Önce güncelle, sonra önceki ham veriden **ağ isteği göndermeden** yeni klasörde rapor üret:

```powershell
git pull --ff-only
$kayit = Get-ChildItem .\output -Filter raw_news_metadata.json -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
.\.venv\Scripts\python.exe -m mapdis_research repair-pilot --input $kayit.DirectoryName
```

Belirli bir denemeyi seçmek için `--input` değerine o çıktı klasörünü yaz. Klasörde `pilot_config.json`, `raw_news_metadata.json`, `collection_status.json` bulunmalıdır. `repair-pilot` yeni zaman damgalı klasör açar; mevcut CSV/JSON dosyalarını ve varsa insan etiketlerini değiştirmez. Yeni üretilen inceleme tablosu ham kayıtlardan oluşturulur; eski tabloda yapılmış insan etiketleri otomatik taşınmaz, eski dosyada korunur. Tamamlanan rapor, geçmiş kaynak hatalarını başarı diye gizlemez. Sıfır kayıt varsa sıfır kalır; hedefe ulaşmış gibi gösterilmez.

`plastic-waste/rss` adresi kullanıcı makinesinde HTTP 404 döndüğü için kaynak şablonunda `available_for_pilot=false` ile işaretlendi; alternatif URL doğrulanmadan tahmin edilmez. Yeni şablonda tüm `enabled` alanları true yapılsa bile bu kaynak atlanır. Eski yerel yapılandırmada hâlâ bulunuyorsa 404 ayrı kaydedilir ve diğer kaynakların verileri korunur.
