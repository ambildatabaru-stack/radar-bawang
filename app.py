import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Radar Bawang Juragan V2", layout="wide")

# --- DATABASE LOKASI ---
# --- DATABASE LOKASI ---
LOCATIONS = {
    "Brebes (Wanasari)": {"lat": -6.88, "lon": 109.02, "region": "Jateng"},
    "Nganjuk (Sukomoro)": {"lat": -7.60, "lon": 111.90, "region": "Jatim"},
    "Demak (Sentra Bawang)": {"lat": -6.89, "lon": 110.64, "region": "Jateng"} 
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
# === TAB 2: RADAR DISKON (Forecast Cuaca) ===
with tab2:
    st.header("🎯 Radar 'Panic Selling' (14 Hari Kedepan)")
    st.caption("Cari daerah dengan curah hujan TINGGI. Petani susah jemur = Harga bisa ditekan.")
    
    df_forecast = get_forecast_data()
    
    if not df_forecast.empty:
        # Tampilkan Grafik
        fig_fore = px.bar(df_forecast, x='Tanggal', y='Curah Hujan (mm)', color='Lokasi', barmode='group',
                          color_discrete_map={
                              "Brebes (Wanasari)": "#EF553B", # Merah
                              "Nganjuk (Sukomoro)": "#00CC96", # Hijau
                              "Demak (Sentra Bawang)": "#FFA15A" # Orange
                          })
        st.plotly_chart(fig_fore, use_container_width=True)
        
        # --- LOGIKA BARU: HUJAN = DISKON ---
        st.subheader("🤑 Analisa Potensi Harga Murah")
        
        # Hitung Total Hujan per Daerah
        summary = df_forecast.groupby("Lokasi")['Curah Hujan (mm)'].sum().reset_index()
        summary = summary.sort_values(by='Curah Hujan (mm)', ascending=False) # Yang paling basah di atas
        
        # Kolom Layout
        col1, col2, col3 = st.columns(3)
        
        # Loop untuk menampilkan Score Card tiap daerah
        cols = [col1, col2, col3]
        for index, row in summary.iterrows():
            loc = row['Lokasi']
            rain_total = row['Curah Hujan (mm)']
            col_obj = cols[index % 3] # Biar rapi ke samping
            
            with col_obj:
                st.markdown(f"#### {loc}")
                st.metric("Total Hujan (2 Minggu)", f"{rain_total:.0f} mm")
                
                # Logic Juragan Bawang Goreng:
                if rain_total > 150:
                    st.success("💰 **PELUANG EMAS!** (Basah Kuyup)")
                    st.markdown("""
                    * **Prediksi:** Petani panik, gak bisa jemur.
                    * **Aksi:** Tawar sadis! Ambil barang basah, langsung goreng.
                    """)
                elif rain_total > 80:
                    st.info("📉 **Potensi Turun** (Basah Sedang)")
                    st.markdown("""
                    * **Prediksi:** Penjemuran terganggu.
                    * **Aksi:** Coba goyang harga sedikit di bawah pasar.
                    """)
                else:
                    st.error("🔥 **Barang Kering** (Harga Keras)")
                    st.markdown("""
                    * **Prediksi:** Cuaca panas, petani santai nyimpen barang.
                    * **Aksi:** Skip dulu, cari daerah lain yg hujan.
                    """)


