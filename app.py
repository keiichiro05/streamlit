# erp_dashboard_streamlit.py
import streamlit as st
import pandas as pd
import numpy as np
import mysql.connector
import plotly.express as px

# --- KONEKSI ke MySQL ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="e-pharm1"
)

# Konfigurasi tampilan
st.set_page_config(layout="wide")
st.title("📦 ERP Monitoring Dashboard")

# Sidebar menu
menu = st.sidebar.selectbox(
    "Pilih Menu",
    [
        "📊 Inventory Monitoring",
        "🚚 Supplier Performance",
        "🚨 Alerts Center",
        "🤖 ML Recommendations",
        "🛡️ Safety Stock Calculator"
    ]
)

# Fungsi load data
@st.cache_data
def load_data():
    products = pd.read_sql_query("SELECT * FROM products", conn)
    warehouse = pd.read_sql_query("SELECT * FROM warehouse", conn)

    # Optional: Load table if available
    try:
        suppliers = pd.read_sql_query("SELECT * FROM suppliers", conn)
    except:
        suppliers = pd.DataFrame()
    
    try:
        po = pd.read_sql_query("SELECT * FROM purchase_orders", conn)
        poi = pd.read_sql_query("SELECT * FROM purchase_order_items", conn)
    except:
        po, poi = pd.DataFrame(), pd.DataFrame()

    try:
        so = pd.read_sql_query("SELECT * FROM sales_orders", conn)
        soi = pd.read_sql_query("SELECT * FROM sales_order_items", conn)
    except:
        so, soi = pd.DataFrame(), pd.DataFrame()

    try:
        tx = pd.read_sql_query("SELECT * FROM inventory_transactions", conn)
    except:
        tx = pd.DataFrame()

    return products, warehouse, suppliers, po, poi, so, soi, tx

# Load all data
products, warehouse, suppliers, po, poi, so, soi, tx = load_data()

# --- 1. Inventory Monitoring ---
if menu == "📊 Inventory Monitoring":
    st.subheader("📦 Inventory Monitoring per Cabang")
    df = warehouse.merge(products[['code', 'stok_minimum']], on='code', how='left')
    cabang_list = sorted(df['cabang'].dropna().unique())
    cabang_select = st.selectbox("Pilih Cabang:", cabang_list)

    df_cabang = df[df['cabang'] == cabang_select].copy()
    df_cabang['Status'] = df_cabang.apply(
        lambda x: "🟢 Aman" if x['jumlah'] >= x['stok_minimum'] else "🔴 Perlu Restok", axis=1
    )

    st.dataframe(df_cabang[['code', 'namabarang', 'kategori', 'jumlah', 'stok_minimum', 'Status']])

    fig = px.bar(
        df_cabang,
        x='namabarang',
        y='jumlah',
        color='Status',
        title='Stok Barang per Cabang',
        labels={'jumlah': 'Jumlah Stok', 'namabarang': 'Nama Barang'}
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 2. Supplier Performance ---
elif menu == "🚚 Supplier Performance":
    st.subheader("🚚 Supplier Performance")
    if not po.empty and not suppliers.empty:
        po_perf = po.merge(suppliers, on='id_supplier', how='left')
        po_perf['tanggal_pesan'] = pd.to_datetime(po_perf['tanggal_pesan'], errors='coerce')
        po_perf['tanggal_terima'] = pd.to_datetime(po_perf['tanggal_terima'], errors='coerce')
        po_perf['lead_time'] = (po_perf['tanggal_terima'] - po_perf['tanggal_pesan']).dt.days

        df_perf = po_perf.groupby('nama_supplier').agg({
            'lead_time': ['mean', 'count']
        }).reset_index()
        df_perf.columns = ['Supplier', 'Avg Lead Time (days)', 'Total Orders']

        st.dataframe(df_perf)

        fig2 = px.bar(
            df_perf,
            x='Supplier',
            y='Avg Lead Time (days)',
            color='Supplier',
            title='Rata-rata Lead Time Supplier'
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Data supplier atau purchase orders tidak tersedia.")

# --- 3. Alerts Center ---
elif menu == "🚨 Alerts Center":
    st.subheader("🚨 Alerts: Barang di Bawah Minimum Stok")
    alert_df = warehouse.merge(products[['code', 'stok_minimum']], on='code', how='left')
    alert_df = alert_df[alert_df['jumlah'] < alert_df['stok_minimum']]
    if alert_df.empty:
        st.success("Semua barang dalam stok aman.")
    else:
        st.dataframe(alert_df[['code', 'namabarang', 'jumlah', 'stok_minimum', 'cabang']])

# --- 4. ML Recommendations ---
elif menu == "🤖 ML Recommendations":
    st.subheader("🤖 Rekomendasi Barang Berdasarkan Prediksi Penjualan")
    if not soi.empty:
        sales_sum = soi.groupby('code').agg({'jumlah': 'sum'}).reset_index()
        sales_sum = sales_sum.merge(products[['code']], on='code', how='left')
        sales_sum['prediksi_minggu_depan'] = (sales_sum['jumlah'] / 12).round().astype(int)

        rekomendasi = warehouse.merge(
            sales_sum[['code', 'prediksi_minggu_depan']],
            on='code',
            how='left'
        )
        rekomendasi['prediksi_minggu_depan'].fillna(0, inplace=True)
        rekomendasi['Butuh Restok'] = rekomendasi['jumlah'] < rekomendasi['prediksi_minggu_depan']

        st.dataframe(rekomendasi[['code', 'namabarang', 'jumlah', 'prediksi_minggu_depan', 'Butuh Restok']])
    else:
        st.warning("Data penjualan tidak tersedia.")

# --- 5. Safety Stock Calculator ---
elif menu == "🛡️ Safety Stock Calculator":
    st.subheader("🛡️ Kalkulasi Safety Stock")
    safety_df = products.copy()
    z = 1.65  # service level 95%
    safety_df['Safety Stock'] = (
        z * np.sqrt(safety_df['deviasi_demand']**2 + safety_df['deviasi_lead_time']**2)
    ).round().astype(int)
    st.dataframe(safety_df[['code', 'namabarang', 'deviasi_demand', 'deviasi_lead_time', 'Safety Stock']])
