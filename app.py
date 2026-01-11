import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# --- KONFIGURASI ---
st.set_page_config(page_title="Radar Bawang Juragan V3", layout="wide")

LOCATIONS = {
    "Brebes (Wanasari)": {"lat": -6.88, "lon": 109.02, "region": "Jateng"},
    "Nganjuk (Sukomoro)": {"lat": -7.60, "lon": 111.90, "region": "Jatim"},
    "Demak (Sentra Bawang)": {"lat": -6.89, "lon": 110.64, "region": "Jateng"}
}

# --- FUNGSI 1: FORECAST (14 Hari - Akurat) ---
def get_forecast_data():
    data_buffer = []
    for loc_name, coords in LOCATIONS.items():
        # Open-Meteo cuma kasih max 14-16 hari gratis
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=precipitation_sum&timezone=Asia%2FBangkok&forecast_days=14"
        try:
            response = requests.get(url).json()
            if 'daily' in response:
                daily_rain = response['daily']['precipitation_sum']
                dates = response['daily']['time']
                for i in range(len(dates)):
                    data_buffer.append({"Tanggal": dates[i], "Lokasi": loc_name, "Curah Hujan (mm)": daily_rain[i], "Tipe": "Real Forecast"})
        except: pass
    return pd.DataFrame(data_buffer)

# --- FUNGSI 2: POLA TAHUNAN (Untuk 2 Bulan ke Depan) ---
def get_seasonal_pattern(future_months=2):
    # Kita ambil data TAHUN LALU di tanggal yang sama sebagai referensi
    today = datetime.date.today()
    start_date = today
    end_date = today + datetime.timedelta(days=future_months*30)
    
    # Mundurin tahunnya ke tahun lalu (2025/2024)
    start_date_past = start_date.replace(year=start_date.year - 1)
    end_date_past = end_date.replace(year=end_date.year - 1)
    
    data_buffer = []
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    
    for loc_name, coords in LOCATIONS.items():
        try:
            params = {
                "latitude": coords['lat'], "longitude": coords['lon'],
                "start_date": start_date_past, "end_date": end_date_past,
                "daily": "precipitation_sum", "timezone": "Asia/Bangkok"
            }
            response = requests.get(base_url, params=params).json()
            
            if 'daily' in response:
                daily_rain = response['daily']['precipitation_sum']
                dates = response['daily']['time']
                
                for i in range(len(dates)):
                    # Kita manipulasi tanggalnya jadi tahun ini biar enak dilihat di grafik
                    date_obj = datetime.datetime.strptime(dates[i], "%Y-%m-%d").date()
                    date_future = date_obj.replace(year=today.year) 
                    
                    data_buffer.append({
                        "Tanggal": date_future, # Tampilkan seolah-olah tahun ini
                        "Lokasi": loc_name,
                        "Curah Hujan (mm)": daily_rain[i],
                        "Tipe": "Pola Tahun Lalu (Referensi)"
                    })
        except: pass
    return pd.DataFrame(data_buffer)

# --- UI DASHBOARD ---
st.title("🧅 Radar Bawang Juragan: Strategi Jangka Panjang")
st.info("💡 **Tips Juragan:** Ramalan cuaca harian cuma valid 2 minggu. Untuk 2 bulan ke depan, kita pakai **Data Historis Tahun Lalu** untuk membaca pola musim.")

tab1, tab2 = st.tabs(["🎯 Taktis (14 Hari)", "🔭 Strategis (2 Bulan)"])

# === TAB 1: REAL FORECAST ===
with tab1:
    st.header("Rencana Jangka Pendek (Eksekusi Sekarang)")
    df_fore = get_forecast_data()
    if not df_fore.empty:
        fig = px.bar(df_fore, x='Tanggal', y='Curah Hujan (mm)', color='Lokasi', barmode='group',
                     color_discrete_map={"Brebes (Wanasari)": "#EF553B", "Nganjuk (Sukomoro)": "#00CC96", "Demak (Sentra Bawang)": "#FFA15A"})
        st.plotly_chart(fig, use_container_width=True)
        
        # Analisa Basah/Diskon
        rain_sum = df_fore.groupby("Lokasi")['Curah Hujan (mm)'].sum().sort_values(ascending=False)
        top_wet = rain_sum.index[0]
        st.success(f"💰 **PELUANG DISKON TERDEKAT:** Daerah **{top_wet}** diprediksi paling basah 2 minggu ini!")

# === TAB 2: LONG TERM PATTERN ===
with tab2:
    st.header("Pola Musim (Prediksi Jangka Panjang)")
    st.markdown("Grafik ini menggunakan data **Tahun Lalu** di tanggal yang sama. Jika tahun lalu banjir, waspada tahun ini juga banjir (Musiman).")
    
    df_season = get_seasonal_pattern(future_months=2) # Tarik 2 bulan
    
    if not df_season.empty:
        # Pake Line Chart biar keliatan tren nya
        fig2 = px.line(df_season, x='Tanggal', y='Curah Hujan (mm)', color='Lokasi',
                       color_discrete_map={"Brebes (Wanasari)": "#EF553B", "Nganjuk (Sukomoro)": "#00CC96", "Demak (Sentra Bawang)": "#FFA15A"})
        st.plotly_chart(fig2, use_container_width=True)
        
        st.subheader("Simpulan Pola (Berdasarkan Sejarah)")
        
        # Hitung akumulasi per bulan
        df_season['Bulan'] = pd.to_datetime(df_season['Tanggal']).dt.strftime('%B')
        monthly_sum = df_season.groupby(['Lokasi', 'Bulan'])['Curah Hujan (mm)'].sum().reset_index()
        
        c1, c2 = st.columns(2)
        
        # Cari data bulan depan (misal Feb) dan depannya lagi (Mar)
        months = df_season['Bulan'].unique()
        
        if len(months) >= 1:
            with c1:
                m1 = months[0]
                st.markdown(f"#### Pola Bulan {m1}")
                data_m1 = monthly_sum[monthly_sum['Bulan'] == m1].sort_values(by='Curah Hujan (mm)', ascending=False)
                st.dataframe(data_m1, hide_index=True)
                wettest = data_m1.iloc[0]['Lokasi']
                st.warning(f"Di bulan {m1} biasanya **{wettest}** paling rawan hujan/banjir.")

        if len(months) >= 2:
            with c2:
                m2 = months[1]
                st.markdown(f"#### Pola Bulan {m2}")
                data_m2 = monthly_sum[monthly_sum['Bulan'] == m2].sort_values(by='Curah Hujan (mm)', ascending=False)
                st.dataframe(data_m2, hide_index=True)
                wettest2 = data_m2.iloc[0]['Lokasi']
                st.warning(f"Di bulan {m2} biasanya **{wettest2}** paling rawan hujan/banjir.")
