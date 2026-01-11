import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Radar Bawang Juragan", layout="wide")

# --- DATABASE LOKASI (Jateng & Jatim) ---
LOCATIONS = {
    "Brebes (Wanasari)": {"lat": -6.88, "lon": 109.02, "region": "Jateng"},
    "Nganjuk (Sukomoro)": {"lat": -7.60, "lon": 111.90, "region": "Jatim"}
}

# --- FUNGSI SEDOT DATA REAL-TIME ---
def get_live_data():
    data_buffer = []
    
    for loc_name, coords in LOCATIONS.items():
        # 1. Tembak API Cuaca (Open-Meteo) - INI DATA ASLI LIVE
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=precipitation_sum&timezone=Asia%2FBangkok&forecast_days=7"
        
        try:
            response = requests.get(url).json()
            # Ambil data hujan 7 hari kedepan
            daily_rain = response['daily']['precipitation_sum']
            dates = response['daily']['time']
            total_rain_week = sum(daily_rain)
            
            # Logic Risiko: Hujan > 50mm seminggu = Bahaya buat bawang
            risk_status = "✅ Aman Terkendali"
            if total_rain_week > 100:
                risk_status = "🔴 BAHAYA (Busuk/Mokoler)"
            elif total_rain_week > 50:
                risk_status = "🟡 Waspada (Rawan Susut)"
            
            # 2. Simulasi Harga (Karena belum ada API Publik Realtime)
            # Nanti bagian ini kita ganti web scrapper beneran
            simulated_price = 24000 if coords['region'] == "Jatim" else 28500
            
            # Masukkan ke keranjang data
            for i in range(len(dates)):
                data_buffer.append({
                    "Tanggal": dates[i],
                    "Lokasi": loc_name,
                    "Curah Hujan (mm)": daily_rain[i],
                    "Total Hujan Mingguan": total_rain_week,
                    "Status Risiko": risk_status,
                    "Estimasi Harga": simulated_price
                })
                
        except Exception as e:
            st.error(f"Gagal narik data untuk {loc_name}: {e}")

    return pd.DataFrame(data_buffer)

# --- TAMPILAN DASHBOARD (FRONTEND) ---
st.title("🧅 Radar Bawang Merah: Brebes vs Nganjuk")
st.markdown("**Intelijen Stok Bahan Baku untuk Juragan Bawang Goreng**")
st.markdown("---")

# Tombol Refresh
if st.button('🔄 Update Data Langsung dari Satelit'):
    st.cache_data.clear()

# Load Data
df = get_live_data()

# Tampilkan Peringatan Dini (Early Warning System)
col_warn1, col_warn2 = st.columns(2)
brebes_risk = df[df['Lokasi'] == "Brebes (Wanasari)"].iloc[0]['Status Risiko']
nganjuk_risk = df[df['Lokasi'] == "Nganjuk (Sukomoro)"].iloc[0]['Status Risiko']

with col_warn1:
    st.info(f"📍 **Status Brebes:** {brebes_risk}")
with col_warn2:
    st.info(f"📍 **Status Nganjuk:** {nganjuk_risk}")

# Visualisasi Grafik
st.subheader("⛈️ Prediksi Hujan 7 Hari ke Depan (Penentu Kualitas)")
st.caption("Grafik batang tinggi = Hujan deras. Hati-hati kadar air tinggi (gorengan jadi lembek/susut banyak).")

fig_rain = px.bar(df, x='Tanggal', y='Curah Hujan (mm)', color='Lokasi', barmode='group',
                  color_discrete_map={"Brebes (Wanasari)": "#EF553B", "Nganjuk (Sukomoro)": "#00CC96"})
st.plotly_chart(fig_rain, use_container_width=True)

# Tabel Detail
with st.expander("Lihat Data Mentah Angka-Angka (Buat Crosscheck)"):
    st.dataframe(df)

# Rekomendasi Cerdas
st.markdown("### 🤖 Rekomendasi Aksi")
rain_brebes_total = df[df['Lokasi']=="Brebes (Wanasari)"]['Total Hujan Mingguan'].iloc[0]
rain_nganjuk_total = df[df['Lokasi']=="Nganjuk (Sukomoro)"]['Total Hujan Mingguan'].iloc[0]

if rain_brebes_total > rain_nganjuk_total + 20:
    st.success("**PELUANG:** Brebes lagi basah kuyup. Fokus cari barang di **Nganjuk** atau daerah timur. Barang Brebes risiko susut tinggi.")
elif rain_nganjuk_total > rain_brebes_total + 20:
    st.success("**PELUANG:** Nganjuk hujan terus. Coba kontak pengepul **Brebes**, cuaca di sana lebih mendukung pengeringan.")
else:
    st.warning("**NETRAL:** Cuaca mirip-mirip. Adu harga saja, Gan!")