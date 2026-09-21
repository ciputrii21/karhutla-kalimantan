# Karhutla Kalimantan — Fire Hotspot Intelligence

End-to-end analysis of Kalimantan forest fires using satellite data and government verified burned-area records.

**[Live dashboard](https://karhutla-kalimantan.streamlit.app/)** *(update after deploy)*

## Data sources

- **NASA FIRMS VIIRS S-NPP 375m** — 1,488,643 fire hotspots, January 2012 – September 2026
- **SiPongi Kementerian Kehutanan** — verified burned area in hectares per province, 2012–2026

*Wajib mencantumkan sumber: SIPONGI KEMENHUT*

## Key findings

**El Niño drives extreme variability.** Hotspot counts range from 17,144 (2022, La Niña) to 370,497 (2015, strong El Niño) — a 21x difference within the same region.

**Hotspot count ≠ burned area.** In 2023, each hotspot corresponded to 5.42 ha burned vs 2.46 ha in 2015. Drier peat in El Niño years allows fire to spread underground, burning far more area per detected hotspot.

**Kalimantan Tengah is the epicenter.** 579,559 hotspots (39% of Kalimantan total), dominated by peatland districts — Pulang Pisau alone accounts for 390,261 ha cumulative burned area.

**2026 season arrived earlier and burns harder.** Peak hotspot activity in August 2026, one month earlier than prior El Niño years. By September, 2026 already exceeds full-year 2019 totals.

**Gradient Boosting outperforms naive baseline significantly.** MAPE 44.1% vs 547.7% naive. Most predictive feature: number of hotspots during peak fire season (June–October), explaining 63.9% of model variance.

## Project structure
src/
cek_firms.py FIRMS API probe and key validation
cek_sp.py Test Standard Processing vs NRT sensors
tarik_firms.py Resumable historical data extraction (1,071 requests)
gabung_firms.py Merge 1,071 CSV chunks into one dataset
clean_sipongi.py Clean SiPongi burned-area Excel exports
notebooks/
01_eksplorasi.ipynb Trend analysis, seasonality, spatial join, model
outputs/
peta_statis_kalimantan.png
prediksi_luas_karhutla.png
app.py Streamlit dashboard

## Data quality notes

- VIIRS SP (Standard Processing) required for historical data — NRT only covers ~90 days
- 4,863 hotspots from Sarawak/Sabah removed via spatial join with GADM shapefile
- Zero values in SiPongi pre-2020 likely reflect incomplete reporting, not absence of fire — percentage of zero-value districts drops from 71% (2016) to 30% (2024)
- SiPongi 2026 data only through July — not comparable to full-year figures
- VIIRS and MODIS hotspot counts are not directly comparable due to resolution difference (375m vs 1km)

## How to replicate

```bash
# 1. Get NASA FIRMS API key: firms.modaps.eosdis.nasa.gov/api/map_key/
# 2. Download SiPongi burned area from sipongi.gakkum.kehutanan.go.id
echo "FIRMS_MAP_KEY=your_key_here" > .env

pip install -r requirements.txt

python3 src/tarik_firms.py       # ~45 minutes, resumable
python3 src/gabung_firms.py
python3 src/clean_sipongi.py
streamlit run app.py
```

## Requirements
pandas
geopandas
folium
streamlit
streamlit-folium
scikit-learn
matplotlib
requests
python-dotenv
openpyxl
