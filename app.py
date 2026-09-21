"""Dashboard Karhutla Kalimantan — NASA FIRMS + SiPongi"""
import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import folium
from streamlit_folium import st_folium
import streamlit as st
import geopandas as gpd

st.set_page_config(page_title="Karhutla Kalimantan", page_icon="🔥", layout="wide")

ROOT = Path(__file__).parent
PROC = ROOT / "data" / "processed"
OUT  = ROOT / "outputs"

@st.cache_data
def muat():
    firms = pd.read_csv(PROC/"firms_dengan_provinsi.csv")
    sipongi = pd.read_csv(PROC/"luas_kalimantan_provinsi.csv")
    with open(OUT/"ringkasan.json") as f:
        ringkasan = json.load(f)
    return firms, sipongi, ringkasan

@st.cache_resource
def muat_geo():
    shp = ROOT/"data"/"raw"/"shapefile"/"gadm41_IDN_1.shp"
    idn = gpd.read_file(shp)
    kal = idn[idn["NAME_1"].isin([
        "Kalimantan Barat","Kalimantan Tengah",
        "Kalimantan Selatan","Kalimantan Timur","Kalimantan Utara"
    ])].copy()
    return kal

firms, sipongi, ringkasan = muat()
kalimantan = muat_geo()

# Header
st.title("🔥 Karhutla Kalimantan")
st.caption("Data: NASA FIRMS VIIRS S-NPP · SiPongi Kementerian Kehutanan · 2012–2026")

k1,k2,k3,k4 = st.columns(4)
k1.metric("Total titik panas", f"{ringkasan['total_titik_panas']:,}")
k2.metric("Tahun terparah (titik)", ringkasan["tahun_terburuk_titik"])
k3.metric("Provinsi episentrum", "Kalteng")
k4.metric("Akurasi model (MAPE)", f"{ringkasan['mape_model_pct']}%")
st.divider()

tab1, tab2, tab3 = st.tabs(["Tren & Intensitas","Peta Sebaran","Model Prediksi"])

with tab1:
    per_tahun = firms.groupby("tahun").agg(
        titik_panas=("frp","count"), frp_mean=("frp","mean")
    ).reset_index()

    el_nino = {2015,2019,2023,2026}
    warna = ["#c0392b" if t in el_nino else "#95a5a6" for t in per_tahun["tahun"]]

    fig, axes = plt.subplots(1,2,figsize=(13,4))
    axes[0].bar(per_tahun["tahun"], per_tahun["titik_panas"]/1000, color=warna, width=0.7)
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_:f"{x:.0f}k"))
    axes[0].set_title("Titik panas per tahun (merah=El Niño)")
    axes[0].set_xlabel("Tahun"); axes[0].set_ylabel("Titik panas (ribu)")

    axes[1].bar(per_tahun["tahun"], per_tahun["frp_mean"], color=warna, width=0.7)
    axes[1].set_title("Rata-rata intensitas api (FRP, MW)")
    axes[1].set_xlabel("Tahun"); axes[1].set_ylabel("FRP rata-rata (MW)")
    plt.tight_layout()
    st.pyplot(fig)

    # Tabel ha per titik
    luas = sipongi[sipongi["tahun_parsial"]==False].groupby("tahun")["luas_ha"].sum().reset_index()
    gabung = per_tahun.merge(luas, on="tahun", how="inner")
    gabung["ha_per_titik"] = (gabung["luas_ha"]/gabung["titik_panas"]).round(2)
    st.subheader("Luas terbakar per titik panas")
    st.info("Nilai tinggi menunjukkan api gambut yang merambat luas meski titik panas sedikit.")
    st.dataframe(gabung[["tahun","titik_panas","luas_ha","ha_per_titik"]]
                 .rename(columns={"tahun":"Tahun","titik_panas":"Titik panas",
                                  "luas_ha":"Luas (ha)","ha_per_titik":"Ha/titik"})
                 .set_index("Tahun"), use_container_width=True)

with tab2:
    rekap_prov = (
        firms.groupby("provinsi")
        .agg(total_titik=("frp","count"), rata_frp=("frp","mean"))
        .reset_index()
    )
    kal_data = kalimantan.merge(rekap_prov, left_on="NAME_1", right_on="provinsi")

    m = folium.Map(location=[-1.5,114.0], zoom_start=6, tiles="CartoDB positron")
    folium.Choropleth(
        geo_data=kal_data.__geo_interface__,
        data=rekap_prov,
        columns=["provinsi","total_titik"],
        key_on="feature.properties.NAME_1",
        fill_color="YlOrRd", fill_opacity=0.75,
        line_opacity=0.5,
        legend_name="Total titik panas 2012–2026",
        highlight=True,
    ).add_to(m)
    for _, row in kal_data.iterrows():
        folium.GeoJson(
            row.geometry.__geo_interface__,
            tooltip=folium.Tooltip(
                f"<b>{row['NAME_1']}</b><br>"
                f"Titik panas: {row['total_titik']:,}<br>"
                f"FRP rata-rata: {row['rata_frp']:.1f} MW"
            ),
            style_function=lambda x:{"fillOpacity":0,"color":"transparent"}
        ).add_to(m)
    st_folium(m, width=900, height=480)
    st.caption("Sumber: NASA FIRMS VIIRS S-NPP 2012–2026 · SIPONGI KEMENHUT")

with tab3:
    st.image(str(OUT/"prediksi_luas_karhutla.png"), use_container_width=True)
    col1, col2 = st.columns(2)
    col1.metric("MAE Model", f"{ringkasan['mae_model_ha']:,} ha")
    col2.metric("MAE Naive", f"{ringkasan['mae_naive_ha']:,} ha")
    st.success(f"Model {ringkasan['mape_model_pct']}% MAPE vs naive 547.7% — "
               f"fitur terpenting: {ringkasan['fitur_terpenting']}")
    st.warning("Model dilatih dari 13 tahun data. Prediksi bersifat indikatif, "
               "bukan untuk keputusan operasional.")
    st.caption("Sumber data luas: SIPONGI KEMENHUT · wajib mencantumkan sumber")