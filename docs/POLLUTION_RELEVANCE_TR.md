# Uydu geçmese de kirliliği yakalama

Hocanın isteği doğrultusunda keşif odağı sensör adından deniz kirliliği bağlamına taşındı. `marine_pollution` varsayılan gelişmiş profildir. Bu profil 93 eşleşme ifadesi içerir; `all` profilinde önceki uydu/yöntem sözlüğüyle birlikte 150 farklı ifade vardır. Eski teknik profiller ayrıca korunur.

```powershell
.\.venv\Scripts\python.exe -m mapdis_research run --profile marine_pollution --max-queries 4 --pages 1
```

## Neyi değerlendirir?

- Kirlilik sinyalleri: petrol, plastik, müsilaj, kanalizasyon/atık su, kimyasal/endüstriyel atık, alg patlaması ve türü belirsiz kirlilik/balık ölümleri.
- Deniz/kıyı bağlamı: deniz, sahil, kıyı, körfez, liman, coast, sea, marine gibi ifadeler.
- Olay sinyalleri: sızma, boşaltılma, kıyıya vurma, raporlanma gibi kaynakta geçen ifadeler.
- Olumsuzluk/belirsizlik: “kirlilik tespit edilmedi”, simülasyon ve olası risk anlatımlarını olay adayı diye etiketlemez.

Sentinel, SAR veya uydu kelimesi şart değildir. Örnek: “Arıtılmamış atık su denize boşaltıldı.” → atık su / deniz bağlamı / olay adayı. “Sentinel-1 heyelan tespit etti.” → ilgili kirlilik kaydı değildir.

Bu yaklaşım açıklanabilir sözlük ve bağlam kurallarıdır; genel amaçlı doğal dil anlama, kusursuz olumsuzluk çözümleme veya olay doğrulaması değildir. Çok karmaşık, dolaylı, yeni eş anlamlı ya da kısa metinlerde yanlış pozitif/negatif olabilir. Kaynak alıntısı ve hangi sinyallerin eşleştiği `pollution_assessment` alanında görünür. Kesin başarı oranı iddia edilmez; gerçek değerlendirme için insan etiketli haber/paper veri kümesi gerekir.

## Paper, haber ve olay birbirine karışmaz

- `academic_research`: API'den gelen yayınlar veya DOI/yayın türüyle tanınan paper'lar. Olaydan bahsetmeleri onları otomatik olay kaydına dönüştürmez.
- `incident_candidate`: haber/web metninde kirlilik, deniz ve olay sinyalleri var; belirsizlik sinyali bulunmadı. Yine de doğrulanmış olay değildir.
- `background_or_ambiguous`: ilgili genel bilgi, risk, olumsuz/varsayımsal anlatım veya yetersiz olay bağlamı.
- `unrelated_or_insufficient_context`: kapsam dışında veya metin yetersiz; geniş profilde elenir.

CSV, JSON, Markdown ve HTML sonuç ekranında değerlendirme görünür. `incident_candidates.json` yalnız adayları, açık bir doğrulanmamışlık uyarısıyla ayrı tutar. Hiçbiri otomatik olarak 16 kolonlu doğrulanmış Notion olay listesine eklenmez. `verified_incident` bu ön elemede her zaman false'dur; bu, olayın gerçek olmadığı değil, bu aşamada doğrulanmadığı anlamına gelir.

## Haber RSS / Atom desteği

`rss` kaynak adaptörü başlık, yayın tarihi, bağlantı ve izinli feed özetini alır. Makalenin tam metnini otomatik indirmez. Bilinmeyen tarihe bugünün tarihini yazmaz. Başka siteleri tarayıp haber kaynağı keşfettiği veya bütün interneti taradığı iddia edilmez.

`config/advanced.json` içinde BBC bilim/çevre feed örneği **kapalı** bulunur. Tercih ettiğin feed'in kullanım koşullarını incele, URL'yi doğrula ve izinli olduğunu belirledikten sonra `enabled` ve `terms_reviewed` alanlarını true yap. robots.txt ve hız sınırları ayrıca kontrol edilir. DTD/entity içeren XML reddedilir. Notion, giriş, paywall veya anti-bot kontrolleri aşılmaz.

2026-10-16 ilk denemede `feeds.bbci.co.uk` isteği proxy tarafından engellendi. Sonraki kontrolde robots.txt ve RSS uç noktası HTTP 200 döndü; robots politikası feed yoluna izin verdi ve 42 gerçek RSS kaydı ayrıştırıldı. Alan adı mevcut API izinleri korunarak ortam taslağına eklendi. Ortam ayarlarında değişikliği inceleyip kaydetmek/yayınlamak gerekir; taslak kaydı çalışan makineye izin uygulandığı anlamına gelmez. BBC kullanım koşullarının yeniden kullanım kapsamı ayrıca incelenene kadar feed otomatik taramada kapalı kalır. RSS/Atom ayrıştırıcısı test örnekleri ve canlı feed metadatası ile doğrulandı. Haberlerin tam metinleri ve olay gerçekliği doğrulanmadı; kapalı feed, otomatik çalışmanın haber topladığı anlamına gelmez. Yerel Windows erişimi ayrıca test edilmelidir.
