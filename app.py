import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- KONFIGURASI ---
st.set_page_config(page_title="Radar Bawang: Battle Royale", layout="wide")

LOCATIONS = {
    "Brebes (Jateng)": {"lat": -6.88, "lon": 109.02},
    "Nganjuk (Jatim)": {"lat": -7.60, "lon": 111.90},
    "Demak (Jateng)": {"lat": -6.89, "lon": 110.64}
}

# --- RUMUS DISKON ALAM (Logika Harga) ---
BASE_PRICE = 32000
PRICE_DROP_PER_MM = 150 
MIN_PRICE = 12000

def calculate_predicted_price(rain_mm):
    drop = rain_mm * PRICE_DROP_PER_MM
    pred_price = BASE_PRICE - drop
    return max(pred_price, MIN_PRICE)

# --- FUNGSI TARIK DATA FORECAST (14 Hari) ---
def get_forecast_for_all():
    all_data = []
    summary_data = []
    
    url = "https://api.open-meteo.com/v1/forecast"
    
    for loc_name, coords in LOCATIONS.items():
        try:
            params = {
                "latitude": coords['lat'],
                "longitude": coords['lon'],
                "daily": "precipitation_sum",
                "timezone": "Asia/Bangkok",
                "forecast_days": 14
            }
            res = requests.get(url, params=params).json()
            
            if 'daily' in res:
                rain = res['daily']['precipitation_sum']
                times = res['daily']['time']
                
                # Buat DataFrame per Lokasi untuk Grafik
                loc_df_data = []
                min_p = 100000
                best_d = ""
                total_r = 0
                
                for i in range(len(times)):
                    r = rain[i]
                    p = calculate_predicted_price(r)
                    loc_df_data.append({"Tanggal": times[i], "Hujan (mm)": r, "Harga (Rp)": p})
                    
                    # Cari harga terendah
                    total_r += r
                    if p < min_p:
                        min_p = p
                        best_d = times[i]
                
                # Simpan data detail
                all_data.append({"Location": loc_name, "Data": pd.DataFrame(loc_df_data)})
                
                # Simpan data ringkasan untuk Klasemen
                summary_data.append({
                    "Daerah": loc_name,
                    "Total Hujan (14 Hari)": round(total_r, 1),
                    "Prediksi Harga Termurah": int(min_p),
                    "Tanggal Terbaik Beli": best_d
                })
                
        except Exception as e:
            pass
            
    return pd.DataFrame(summary_data), all_data

# --- FUNGSI GAMBAR GRAFIK ---
def plot_chart(df, title):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df['Tanggal'], y=df['Hujan (mm)'], name="Hujan", marker_color='#3366CC', opacity=0.4), secondary_y=False)
    fig.add_trace(go.Scatter(x=df['Tanggal'], y=df['Harga (Rp)'], name="Harga", mode='lines+markers', line=dict(color='#DC3912', width=3)), secondary_y=True)
    
    fig.update_layout(
        title=title, 
        title_font_size=14,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350
    )
    fig.update_yaxes(title_text="mm", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="Rp", secondary_y=True, range=[10000, 35000])
    return fig

# --- DASHBOARD UTAMA ---
st.title("🧅 Radar Bawang: Komparasi 3 Kota")
st.caption("Pantauan Serentak: Brebes vs Nganjuk vs Demak")

# 1. Tarik Data
summary_df, detailed_data = get_forecast_for_all()

# 2. TAMPILKAN KLASEMEN (LEAGUE TABLE)
if not summary_df.empty:
    st.subheader("🏆 Klasemen: Dimana Barang Termurah?")
    
    # Urutkan dari yang harganya paling murah
    summary_df = summary_df.sort_values(by="Prediksi Harga Termurah", ascending=True).reset_index(drop=True)
    
    # Tampilkan pakai Metric Cards biar ganteng
    cols = st.columns(3)
    for index, row in summary_df.iterrows():
        with cols[index]:
            st.markdown(f"### Juara {index+1}: {row['Daerah']}")
            st.metric("Target Harga", f"Rp {row['Prediksi Harga Termurah']:,.0f}", f"Tgl: {row['Tanggal Terbaik Beli']}")
            
            if row['Total Hujan (14 Hari)'] > 100:
                st.error(f"🌧️ Basah Kuyup ({row['Total Hujan (14 Hari)']} mm)")
            elif row['Total Hujan (14 Hari)'] > 50:
                st.warning(f"🌦️ Hujan Sedang ({row['Total Hujan (14 Hari)']} mm)")
            else:
                st.success(f"☀️ Kering ({row['Total Hujan (14 Hari)']} mm)")

    st.markdown("---")

# 3. GRAFIK JEJER TIGA (BATTLE VIEW)
st.subheader("📊 Detail Grafik Per Daerah (14 Hari ke Depan)")

if detailed_data:
    # Bikin 3 kolom
    col1, col2, col3 = st.columns(3)
    columns_list = [col1, col2, col3]
    
    # Loop biar otomatis ngisi kolom
    for i, item in enumerate(detailed_data):
        loc_name = item['Location']
        df_loc = item['Data']
        
        # Tentukan mau ditaro di kolom mana
        current_col = columns_list[i % 3]
        
        with current_col:
            st.markdown(f"**{loc_name}**")
            fig = plot_chart(df_loc, f"Tren {loc_name}")
            st.plotly_chart(fig, use_container_width=True)
            
            # Cari hari paling hujan di daerah ini
            max_rain = df_loc['Hujan (mm)'].max()
            max_date = df_loc.loc[df_loc['Hujan (mm)'].idxmax()]['Tanggal']
            st.caption(f"Puncak Hujan: {max_date} ({max_rain:.1f} mm)")

else:
    st.error("Gagal menarik data cuaca. Coba refresh.")
