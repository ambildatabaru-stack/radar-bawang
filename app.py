import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Radar Bawang Juragan V2", layout="wide")

# --- DATABASE LOKASI ---
LOCATIONS = {
    "Brebes (Wanasari)": {"lat": -6.88, "lon": 109.02, "region": "Jateng"},
    "Nganjuk (Sukomoro)": {"lat": -7.60, "lon": 111.90, "region": "Jatim"}
}

# --- FUNGSI 1: TARIK DATA HISTORIS (Masa Lalu) ---
def get_historical_data(start_date, end_date):
    data_buffer = []
    # API Archive Open-Meteo (Khusus Data Lampau)
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    
    for loc_name, coords in LOCATIONS.items():
        try:
            params = {
                "latitude": coords['lat'],
                "longitude": coords['lon'],
                "start_date": start_date,
                "end_date": end_date,
                "daily": "precipitation_sum",
                "timezone": "Asia/Bangkok"
            }
            response = requests.get(base_url, params=params).json()
            
            if 'daily' in response:
                daily_rain = response['daily']['precipitation_sum']
                dates = response['daily']['time']
                
                for i in range(len(dates)):
                    # Logic: Hujan > 20mm sehari itu udah bikin tanah becek parah
                    status = "Kering"
                    if daily_rain[i] > 50: status = "BANJIR/EXTREME"
                    elif daily_rain[i] > 10: status = "Hujan"
                    
                    data_buffer.append({
                        "Tanggal": dates[i],
                        "Lokasi": loc_name,
                        "Curah Hujan (mm)": daily_rain[i],
                        "Status": status
                    })
        except Exception as e:
            st.error(f"Gagal tarik history {loc_name}: {e}")
            
    return pd.DataFrame(data_buffer)

# --- FUNGSI 2: TARIK DATA FORECAST (Masa Depan) ---
def get_forecast_data():
    data_buffer = []
    for loc_name, coords in LOCATIONS.items():
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&daily=precipitation_sum&timezone=Asia%2FBangkok&forecast_days=14"
        try:
            response = requests.get(url).json()
            daily_rain = response['daily']['precipitation_sum']
            dates = response['daily']['time']
            
            for i in range(len(dates)):
                data_buffer.append({
                    "Tanggal": dates[i],
                    "Lokasi": loc_name,
                    "Curah Hujan (mm)": daily_rain[i]
                })
        except Exception as e:
            pass # Silent error biar gak ngerusak tampilan
    return pd.DataFrame(data_buffer)

# --- UI DASHBOARD ---
st.title("🧅 Intelijen Bawang Merah: Nganjuk vs Brebes")
st.write(f"Tanggal Hari Ini: {datetime.date.today()}")

# Bikin 2 Tab: Masa Lalu & Masa Depan
tab1, tab2 = st.tabs(["📜 Audit Masa Lalu (Des-Jan)", "🔭 Radar Masa Depan (Feb/Forecast)"])

# === TAB 1: AUDIT DATA (Masa Lalu) ===
with tab1:
    st.header("Cek Fakta Lapangan (Desember - Kemarin)")
    st.info("Gunakan ini untuk memvalidasi alasan supplier. Apakah benar kemarin banjir?")
    
    # Input Rentang Tanggal
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_d = st.date_input("Mulai Tanggal", datetime.date(2025, 12, 1))
    with col_date2:
        end_d = st.date_input("Sampai Tanggal", datetime.date.today() - datetime.timedelta(days=2)) # Data history biasanya delay 2 hari
    
    if st.button("Tarik Data History"):
        if start_d > end_d:
            st.error("Tanggal mulai gak boleh lebih besar dari tanggal akhir, Gan!")
        else:
            with st.spinner("Sedang mengaudit data satelit..."):
                df_hist = get_historical_data(start_d, end_d)
                
                if not df_hist.empty:
                    # 1. Total Curah Hujan (Siapa paling basah?)
                    total_rain = df_hist.groupby("Lokasi")["Curah Hujan (mm)"].sum().reset_index()
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.subheader("Total Hujan (Akumulasi)")
                        st.dataframe(total_rain)
                        brebes_rain = total_rain[total_rain['Lokasi'].str.contains("Brebes")]['Curah Hujan (mm)'].sum()
                        nganjuk_rain = total_rain[total_rain['Lokasi'].str.contains("Nganjuk")]['Curah Hujan (mm)'].sum()
                        
                        if brebes_rain > nganjuk_rain:
                            st.warning("⚠️ **Brebes Lebih Basah** di periode ini. Hati-hati barang lembab.")
                        else:
                            st.warning("⚠️ **Nganjuk Lebih Basah** di periode ini.")

                    with c2:
                        st.subheader("Grafik Tren Hujan Harian")
                        fig_hist = px.line(df_hist, x='Tanggal', y='Curah Hujan (mm)', color='Lokasi', markers=True,
                                           color_discrete_map={"Brebes (Wanasari)": "#EF553B", "Nganjuk (Sukomoro)": "#00CC96"})
                        # Kasih garis batas bahaya
                        fig_hist.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Batas Bahaya (20mm)")
                        st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.warning("Data tidak ditemukan atau error koneksi.")

# === TAB 2: FORECAST (Masa Depan) ===
with tab2:
    st.header("Prediksi 14 Hari Kedepan (Masuk Februari)")
    st.caption("Data ini adalah ramalan cuaca. Semakin jauh tanggalnya, akurasi makin turun.")
    
    df_forecast = get_forecast_data()
    
    if not df_forecast.empty:
        fig_fore = px.bar(df_forecast, x='Tanggal', y='Curah Hujan (mm)', color='Lokasi', barmode='group',
                          color_discrete_map={"Brebes (Wanasari)": "#EF553B", "Nganjuk (Sukomoro)": "#00CC96"})
        st.plotly_chart(fig_fore, use_container_width=True)
        
        # Analisa Cepat
        st.subheader("🤖 Analisa Juragan")
        future_rain_brebes = df_forecast[df_forecast['Lokasi'].str.contains("Brebes")]['Curah Hujan (mm)'].sum()
        future_rain_nganjuk = df_forecast[df_forecast['Lokasi'].str.contains("Nganjuk")]['Curah Hujan (mm)'].sum()
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.metric("Potensi Hujan Brebes (2 Minggu)", f"{future_rain_brebes:.1f} mm")
        with col_res2:
            st.metric("Potensi Hujan Nganjuk (2 Minggu)", f"{future_rain_nganjuk:.1f} mm")
            
        if future_rain_brebes < 50 and future_rain_nganjuk > 100:
            st.success("🎯 **Target Operasi:** BREBES! Cuaca di sana diprediksi lebih kering.")
        elif future_rain_nganjuk < 50 and future_rain_brebes > 100:
            st.success("🎯 **Target Operasi:** NGANJUK! Cuaca di sana diprediksi lebih kering.")
        else:
            st.info("⚖️ Cuaca relatif sama. Mainkan harga!")
