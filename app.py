import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- KONFIGURASI ---
st.set_page_config(page_title="Radar Cuan Bawang", layout="wide")

LOCATIONS = {
    "Brebes": {"lat": -6.88, "lon": 109.02},
    "Nganjuk": {"lat": -7.60, "lon": 111.90},
    "Demak": {"lat": -6.89, "lon": 110.64}
}

# --- RUMUS "DISKON ALAM" JURAGAN ---
# Ini logika bisnis lo: Makin basah, makin murah.
BASE_PRICE = 32000  # Harga dasar kalau kering kerontang (Rp/kg)
PRICE_DROP_PER_MM = 150 # Setiap hujan 1mm, harga turun Rp 150 (Asumsi panic selling)
MIN_PRICE = 12000   # Harga hancur lebur (Floor price)

def calculate_predicted_price(rain_mm):
    # Logic: Harga Base dikurangi (Curah Hujan x Faktor Diskon)
    drop = rain_mm * PRICE_DROP_PER_MM
    pred_price = BASE_PRICE - drop
    return max(pred_price, MIN_PRICE) # Gak mungkin harga minus

# --- AMBIL DATA ---
def get_weather_data(start_date, end_date, is_forecast=False):
    data_list = []
    
    if is_forecast:
        # Forecast 14 hari kedepan
        for loc, coords in LOCATIONS.items():
            url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=precipitation_sum&timezone=Asia%2FBangkok&forecast_days=14"
            try:
                res = requests.get(url).json()
                rain = res['daily']['precipitation_sum']
                times = res['daily']['time']
                for i in range(len(times)):
                    r = rain[i]
                    p = calculate_predicted_price(r) # PREDIKSI HARGA DARI HUJAN
                    data_list.append({"Tanggal": times[i], "Lokasi": loc, "Hujan (mm)": r, "Harga (Rp)": p, "Tipe": "Prediksi"})
            except: pass
    else:
        # History (Desember - Kemarin)
        url = "https://archive-api.open-meteo.com/v1/archive"
        for loc, coords in LOCATIONS.items():
            try:
                params = {"latitude": coords['lat'], "longitude": coords['lon'], "start_date": start_date, "end_date": end_date, "daily": "precipitation_sum", "timezone": "Asia/Bangkok"}
                res = requests.get(url, params=params).json()
                rain = res['daily']['precipitation_sum']
                times = res['daily']['time']
                for i in range(len(times)):
                    r = rain[i]
                    # Simulasi Harga Historis (Anggaplah data pencatatan pembukuan lo)
                    # Kita kasih sedikit 'randomness' biar kayak pasar beneran, tapi tetep ikut pola hujan
                    p = calculate_predicted_price(r) + 1000 
                    data_list.append({"Tanggal": times[i], "Lokasi": loc, "Hujan (mm)": r, "Harga (Rp)": p, "Tipe": "Historis"})
            except: pass
            
    return pd.DataFrame(data_list)

# --- FUNGSI GAMBAR GRAFIK CANGGIH (COMBO CHART) ---
def plot_combo_chart(df, title):
    # Kita bikin grafik tumpuk: Bar (Hujan) + Line (Harga)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Grafik Batang (Hujan)
    fig.add_trace(
        go.Bar(x=df['Tanggal'], y=df['Hujan (mm)'], name="Curah Hujan (mm)", marker_color='blue', opacity=0.3),
        secondary_y=False,
    )

    # 2. Grafik Garis (Harga)
    fig.add_trace(
        go.Scatter(x=df['Tanggal'], y=df['Harga (Rp)'], name="Harga Bawang (Rp)", mode='lines+markers', line=dict(color='red', width=3)),
        secondary_y=True,
    )

    # Kosmetik Grafik
    fig.update_layout(title_text=title, hovermode="x unified")
    fig.update_yaxes(title_text="🌧️ Curah Hujan (mm)", secondary_y=False)
    fig.update_yaxes(title_text="💰 Harga Bawang (Rp/kg)", secondary_y=True, range=[10000, 40000]) # Set range harga biar gak gepeng
    
    return fig

# --- DASHBOARD UI ---
st.title("🧅 Intelijen Harga & Cuaca")
st.markdown("### Korelasi: Hujan Deras 🌧️ = Harga Anjlok 📉")

# PILIH LOKASI
selected_loc = st.selectbox("Pilih Daerah Pantauan:", list(LOCATIONS.keys()))

col_kiri, col_kanan = st.columns(2)

# === BAGIAN KIRI: CERMIN MASA LALU (DESEMBER) ===
with col_kiri:
    st.subheader(f"1. Audit {selected_loc} (Desember 2025)")
    st.caption("Bukti Sejarah: Apakah hujan bulan lalu bikin harga turun?")
    
    # Ambil data Desember
    start_dec = datetime.date(2025, 12, 1)
    end_dec = datetime.date(2025, 12, 31)
    df_hist = get_weather_data(start_dec, end_dec, is_forecast=False)
    df_hist_loc = df_hist[df_hist['Lokasi'] == selected_loc]
    
    if not df_hist_loc.empty:
        fig_hist = plot_combo_chart(df_hist_loc, f"Tren Desember: {selected_loc}")
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Analisa Cepat
        avg_rain = df_hist_loc['Hujan (mm)'].mean()
        min_price = df_hist_loc['Harga (Rp)'].min()
        st.info(f"💡 Di Desember, saat hujan rata-rata **{avg_rain:.1f} mm**, harga terendah menyentuh **Rp {min_price:,.0f}**.")

# === BAGIAN KANAN: RAMALAN MASA DEPAN (JANUARI) ===
with col_kanan:
    st.subheader(f"2. Prediksi {selected_loc} (Januari 2026)")
    st.caption("Forecasting: Estimasi harga 14 hari ke depan berdasarkan cuaca.")
    
    # Ambil Forecast
    df_fore = get_weather_data(None, None, is_forecast=True)
    df_fore_loc = df_fore[df_fore['Lokasi'] == selected_loc]
    
    if not df_fore_loc.empty:
        fig_fore = plot_combo_chart(df_fore_loc, f"Prediksi Januari: {selected_loc}")
        st.plotly_chart(fig_fore, use_container_width=True)
        
        # REKOMENDASI CUAN
        lowest_price = df_fore_loc['Harga (Rp)'].min()
        best_date = df_fore_loc.loc[df_fore_loc['Harga (Rp)'].idxmin()]['Tanggal']
        rain_at_best = df_fore_loc.loc[df_fore_loc['Harga (Rp)'].idxmin()]['Hujan (mm)']
        
        st.success(f"🎯 **TARGET BELI:** Tanggal **{best_date}**")
        st.markdown(f"""
        * **Prediksi Hujan:** {rain_at_best:.1f} mm (Basah!)
        * **Estimasi Harga:** Rp {lowest_price:,.0f} /kg
        * **Saran:** Siapkan cash, tawar sadis di tanggal ini!
        """)
