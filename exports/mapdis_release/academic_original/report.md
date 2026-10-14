# Sentinel-1 SAR oil-spill detection: 10 citation-verified papers

## Scope and verification

The existing sample configuration was run unchanged, returning 100 raw API records and 64 deduplicated records (see ../live_sample). Its broad queries were supplemented by one targeted OpenAlex query: `oil spill Sentinel-1 detection`, filtered to articles published from 2020-01-01, 50 candidates. Ten journal papers with explicit Sentinel-1/oil-spill relevance in their titles/abstracts were selected; this is a purposive bibliography, not a systematic review. Each DOI and title was checked against a live Crossref DOI lookup (title similarity >95%); raw responses are retained. Both API endpoints returned HTTP 200. No LLM was used.

Verification covers citation identity and retrieved abstract statements, not replication of experiments or full-text verification. OpenAlex publication dates and Crossref date-parts are retained separately; online and issue dates may differ.

## Paper evidence

### [1] A near real-time automated oil spill detection and early warning system using Sentinel-1 SAR imagery for the Southeastern Mediterranean Sea

Date (OpenAlex): 2024-03-07; journal (Crossref): International Journal of Remote Sensing

DOI citation: <https://doi.org/10.1080/01431161.2024.2321468>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4392550991) · [Crossref](https://api.crossref.org/works/10.1080%2F01431161.2024.2321468)

Extractive abstract summary:

```text
The ecological and environmental impact of marine oil pollution underlines the importance and necessity of an oil spill surveillance system. This study proposed an operational automated oil spill detection and early warning system to help take quick action for oil combating operations. Oil slicks in the spaceborne Sentinel-1 synthetic aperture radar (SAR) data are detected by a trained deep learning-based oil object detector.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4392550991)

### [2] A self-evolving deep learning algorithm for automatic oil spill detection in Sentinel-1 SAR images

Date (OpenAlex): 2023-11-01; journal (Crossref): Remote Sensing of Environment

DOI citation: <https://doi.org/10.1016/j.rse.2023.113872>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4388168602) · [Crossref](https://api.crossref.org/works/10.1016%2Fj.rse.2023.113872)

Extractive abstract summary:

```text
Oil spill accidents are one of the major problems causing marine pollution, and thus such accidents require rapid detection for early response. In recent years, deep learning algorithms for oil spill detection have been developed for analyzing SAR images. Nevertheless, to generation of deep learning training data using visual inspection is not only a time-consuming and labor-intensive, but also cause bias and lack of diversity in oil slick training data.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4388168602)

### [3] A deep learning based oil spill detector using Sentinel-1 SAR imagery

Date (OpenAlex): 2022-06-03; journal (Crossref): International Journal of Remote Sensing

DOI citation: <https://doi.org/10.1080/01431161.2022.2109445>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4292601150) · [Crossref](https://api.crossref.org/works/10.1080%2F01431161.2022.2109445)

Extractive abstract summary:

```text
The Eastern Mediterranean Sea has been known as an oil pollution hotspot due to its heavy marine traffic and an increasing number of oil and gas exploration activities. To provide automatic detection of oil pollution from not only maritime accidents but also deliberate discharges in this region, a deep learning-based object detector was developed utilizing freely available Sentinel-1 Synthetic Aperture Radar (SAR) imagery. A total of 9768 oil objects were collected from 5930 Sentinel-1 scenes from 2015 to 2018 and used for training and validating the object detector and evaluating its performance.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4292601150)

### [4] A Semi-Empirical Threshold Model for Oil Spill Detection by Analyzing Microwave Backscatter of Ocean Surface From Sentinel-1 C-Band SAR Data

Date (OpenAlex): 2024-01-01; journal (Crossref): IEEE Geoscience and Remote Sensing Letters

DOI citation: <https://doi.org/10.1109/lgrs.2024.3355464>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4391248650) · [Crossref](https://api.crossref.org/works/10.1109%2Flgrs.2024.3355464)

Extractive abstract summary:

```text
In this letter, we present a new semi-empirical approach for optimized dark spot detection. The proposed method is a C-band model that identifies oil spill candidates by correlating surface wind vectors and incidence angles with SAR threshold backscatter coefficients. Specifically, our approach combines insights from wind-wave generation and radar imaging theories with the 193 global Sentinel-1 SAR oil spill data.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4391248650)

### [5] Deep neural network for oil spill detection using Sentinel-1 data: application to Egyptian coastal regions

Date (OpenAlex): 2022-12-13; journal (Crossref): Geomatics, Natural Hazards and Risk

DOI citation: <https://doi.org/10.1080/19475705.2022.2155998>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4311239753) · [Crossref](https://api.crossref.org/works/10.1080%2F19475705.2022.2155998)

Extractive abstract summary:

```text
Building an oil spill segmentation model is very challenging because of the limited available information on oil spill accidents. Therefore, this paper proposes a custom data generator based on Segmentation Network (Seg-Net) model implemented in Conditional Generative Adversarial Network (CGAN). The proposed model is trained for oil spill segmentation using 50 Sentinal-1 Synthetic Aperture Radar (SAR) images.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4311239753)

### [6] Marine Oil Spill Detection from SAR Images Based on Attention U-Net Model Using Polarimetric and Wind Speed Information

Date (OpenAlex): 2022-09-28; journal (Crossref): International Journal of Environmental Research and Public Health

DOI citation: <https://doi.org/10.3390/ijerph191912315>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4297522844) · [Crossref](https://api.crossref.org/works/10.3390%2Fijerph191912315)

Extractive abstract summary:

```text
With the rapid development of marine trade, marine oil pollution is becoming increasingly severe, which can exert damage to the health of the marine environment. Therefore, detection of marine oil spills is important for effectively starting the oil-spill cleaning process and the protection of the marine environment. The polarimetric synthetic aperture radar (PolSAR) technique has been applied to the detection of marine oil spills in recent years.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4297522844)

### [7] Oil Spill Detection with Dual-Polarimetric Sentinel-1 SAR Using Superpixel-Level Image Stretching and Deep Convolutional Neural Network

Date (OpenAlex): 2022-08-11; journal (Crossref): Remote Sensing

DOI citation: <https://doi.org/10.3390/rs14163900>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4290999455) · [Crossref](https://api.crossref.org/works/10.3390%2Frs14163900)

Extractive abstract summary:

```text
Synthetic aperture radar (SAR) has been widely applied in oil spill detection on the sea surface due to the advantages of wide area coverage, all-weather operation, and multi-polarization characteristics. Sentinel-1 satellites can provide dual-polarized SAR data, and they have high potential for successful application to oil spill detection. However, the characteristics of the sea surface and oil film on different images are not the same when imaging at different locations and in different conditions, which leads to the inconsistent accuracy of these images with the application of the current oil spill detection methods.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4290999455)

### [8] Deep-water oil-spill monitoring and recurrence analysis in the Brazilian territory using Sentinel-1 time series and deep learning

Date (OpenAlex): 2022-01-29; journal (Crossref): International Journal of Applied Earth Observation and Geoinformation

DOI citation: <https://doi.org/10.1016/j.jag.2022.102695>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W4210680518) · [Crossref](https://api.crossref.org/works/10.1016%2Fj.jag.2022.102695)

Extractive abstract summary:

```text
Oil spills are a worldwide concern since they cause environmental problems and financial losses. Automatic detection plays a crucial role in rapid decision-making to reduce damage. In this context, deep learning and remote sensing are powerful tools with successful applications in many regions.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W4210680518)

### [9] Oil Spill Detection Based on Deep Convolutional Neural Networks Using Polarimetric Scattering Information From Sentinel-1 SAR Images

Date (OpenAlex): 2021-11-08; journal (Crossref): IEEE Transactions on Geoscience and Remote Sensing

DOI citation: <https://doi.org/10.1109/tgrs.2021.3126175>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W3213954057) · [Crossref](https://api.crossref.org/works/10.1109%2Ftgrs.2021.3126175)

Extractive abstract summary:

```text
Oil spill accidents can cause severe ecological disasters; hence, the timely and effective detection of oil spills on the marine surface is of great significance. Synthetic aperture radar (SAR) is very suitable for large-scale oil spill monitoring. As a more advanced form of SAR, polarimetric SAR (PolSAR) can provide more scattering information of land objects, which can help to improve the accuracy of oil spill detection.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W3213954057)

### [10] SAR Oil Spill Detection System through Random Forest Classifiers

Date (OpenAlex): 2021-05-22; journal (Crossref): Remote Sensing

DOI citation: <https://doi.org/10.3390/rs13112044>

Metadata checks: [OpenAlex](https://api.openalex.org/works/W3165006992) · [Crossref](https://api.crossref.org/works/10.3390%2Frs13112044)

Extractive abstract summary:

```text
A set of open-source routines capable of identifying possible oil-like spills based on two random forest classifiers were developed and tested with a Sentinel-1 SAR image dataset. The first random forest model is an ocean SAR image classifier where the labeling inputs were oil spills, biological films, rain cells, low wind regions, clean sea surface, ships, and terrain. The second one was a SAR image oil detector named “Radar Image Oil Spill Seeker (RIOSS)”, which classified oil-like targets.
```

Supporting source: [OpenAlex abstract](https://api.openalex.org/works/W3165006992)

## Synthesis, disagreements, and missing information

The selected papers describe deep neural networks with polarimetric features ([9](https://doi.org/10.1109/tgrs.2021.3126175)), operational detection ([1](https://doi.org/10.1080/01431161.2024.2321468)), a semi-empirical threshold method ([4](https://doi.org/10.1109/lgrs.2024.3355464)), and random-forest classification ([10](https://doi.org/10.3390/rs13112044)). These are author-reported approaches; the retrieved abstracts do not establish a shared benchmark.

No factual disagreement is established by this bibliography. Different methods and reported metrics are not directly comparable without matching datasets, labeling protocols, sea states, and validation procedures. No claim of a universally best model or numerical cross-study comparison is made.

Full texts, independent ground truth, consistent evaluation datasets, reproducibility, licensing of training imagery, and deployment performance were not verified. Retracted status was checked only in OpenAlex discovery metadata. Citation agreement between two aggregators does not establish scientific correctness or independent factual corroboration.

## Reproducibility and artifacts

`results.json` and `results.csv` contain exactly 10 distinct DOI records with retrieved abstract text and excerpts. `verification.json` stores live verification endpoints, authors, journal metadata and UTC check times. `openalex_discovery.json` and `crossref_*.json` preserve the actual API responses. `run.json` records completion. No website scraping or paywall access was needed.
