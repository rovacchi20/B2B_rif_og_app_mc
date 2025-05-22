# app.py: Streamlit dashboard ottimizzato con caricamento "lazy" e filtering on-demand
import streamlit as st
import pandas as pd

# -------------------------------------------
# Configurazione pagina
# -------------------------------------------
st.set_page_config(page_title="Dashboard Prodotti & Applicazioni", layout="wide")
st.markdown(
    """
    <style>
      .main > .block-container { padding:1rem 2rem; }
      h1 { font-size:2.5rem; color:#334155; margin-bottom:0.5rem; }
      .sidebar .sidebar-content { background-color:#F1F5F9; padding:1rem; border-radius:8px; }
      .stButton>button { background-color:#2563EB; color:white; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------
# Sidebar: upload file
# -------------------------------------------
with st.sidebar:
    st.markdown("## 📥 Carica i file Excel")
    prod_file = st.file_uploader("Dati Prodotti", type=["xlsx","xls"])
    ref_file  = st.file_uploader("Riferimenti Originali", type=["xlsx","xls"])
    app_file  = st.file_uploader("Applicazioni Macchine", type=["xlsx","xls"])

if not (prod_file and ref_file and app_file):
    st.sidebar.warning("Carica tutti e tre i file per procedere.")
    st.stop()

# -------------------------------------------
# Caricamenti base (solo metadati) cached
# -------------------------------------------
@st.cache_data
def load_basic_products(f):
    f.seek(0)
    # carica solo le colonne necessarie per iniziare
    return pd.read_excel(f, usecols=["product_code","category_text"], dtype=str)

@st.cache_data
def load_basic_references(f):
    f.seek(0)
    return pd.read_excel(f, usecols=["code","company_name","relation_code"], dtype=str)

@st.cache_data
def load_basic_applications(f):
    f.seek(0)
    return pd.read_excel(f, usecols=["code","company_name","relation_code"], dtype=str)

# -------------------------------------------
# Caricamenti full on-demand
# -------------------------------------------
@st.cache_data
def load_full_products(f):
    f.seek(0)
    return pd.read_excel(f, dtype=str)

@st.cache_data
def load_full_references(f):
    f.seek(0)
    return pd.read_excel(f, dtype=str)

@st.cache_data
def load_full_applications(f):
    f.seek(0)
    return pd.read_excel(f, dtype=str)

# -------------------------------------------
# Setup iniziale dei filtri
# -------------------------------------------
df_basic = load_basic_products(prod_file)
categories = sorted(df_basic['category_text'].dropna().unique())
skus_all = sorted(df_basic['product_code'].str.lstrip('0').dropna().unique())

col1, col2 = st.columns(2)
with col1:
    sel_cat = st.selectbox("Category Text", [""] + categories)
with col2:
    # se ho una categoria, limito gli SKU al subset
    if sel_cat:
        skus = sorted(
            df_basic[df_basic['category_text']==sel_cat]['product_code']
                   .str.lstrip('0').dropna().unique()
        )
    else:
        skus = skus_all
    sel_sku = st.selectbox("Filtra per SKU", [""] + skus)

# -------------------------------------------
# Logica on-demand
# -------------------------------------------
if sel_cat or sel_sku:
    # Carico i dati completi solo per il subset selezionato
    df_prod_full = load_full_products(prod_file)
    # mantengo solo righe di interesse
    df_view = df_prod_full
    if sel_cat:
        df_view = df_view[df_view['category_text']==sel_cat]
    if sel_sku:
        df_view = df_view[df_view['product_code'].str.lstrip('0')==sel_sku]

    # Carico riferimenti full e preparo pivot solo sui codici usati
    df_ref_full = load_full_references(ref_file)
    temp = df_ref_full[df_ref_full['code'].isin(
        df_view['product_code'].str.lstrip('0')
    )].copy()
    temp['idx'] = temp.groupby('code').cumcount()+1
    piv = temp.pivot(index='code', columns='idx', values=['company_name','relation_code'])
    piv.columns = [f"brand{i}" if c=='company_name' else f"reference{i}" for c,i in piv.columns]
    piv = piv.reset_index().rename(columns={'code':'sku'})
    piv['sku_stripped'] = piv['sku'].str.lstrip('0')

    # Merge su df_view
    df_view['prod_stripped'] = df_view['product_code'].str.lstrip('0')
    merged = df_view.merge(
        piv, left_on='prod_stripped', right_on='sku_stripped', how='left'
    )

    # Mostro multiselect colonne dinamico
    # prendo le colonne non-NaN di merged
    available = [c for c in merged.columns if merged[c].notna().any()]
    sel_cols = st.multiselect("Colonne da mostrare", available, default=available)
    if sel_cols:
        st.dataframe(merged[sel_cols].reset_index(drop=True), use_container_width=True)
else:
    st.info("Seleziona almeno una categoria o uno SKU per caricare i dati.")

# -------------------------------------------
# Tab Riferimenti e Applicazioni (base)
# -------------------------------------------
t2, t3 = st.tabs(["Riferimenti","Applicazioni"])
with t2:
    df_ref_basic = load_basic_references(ref_file)
    b_opts = sorted(df_ref_basic['company_name'].dropna().unique())
    r_opts = sorted(df_ref_basic['relation_code'].dropna().unique())
    # Filtro per Brand
    sel_br = st.multiselect("Brand", b_opts)
    # Filtro per Reference
    sel_rr = st.multiselect("Reference", r_opts)
    # Filtro per Code
    code_opts = sorted(df_ref_basic['code'].dropna().unique())
    sel_code = st.multiselect("Code", code_opts)
    df_ref_view = df_ref_basic
    if sel_br:
        df_ref_view = df_ref_view[df_ref_view['company_name'].isin(sel_br)]
    if sel_rr:
        df_ref_view = df_ref_view[df_ref_view['relation_code'].isin(sel_rr)]
    if sel_code:
        df_ref_view = df_ref_view[df_ref_view['code'].isin(sel_code)]
    st.dataframe(df_ref_view.reset_index(drop=True), use_container_width=True).reset_index(drop=True), use_container_width=True)

with t3:
    df_app_basic = load_basic_applications(app_file)
    ba_opts = sorted(df_app_basic['company_name'].dropna().unique())
    ra_opts = sorted(df_app_basic['relation_code'].dropna().unique())
    sel_ba = st.multiselect("Brand Applicazione", ba_opts)
    sel_ra = st.multiselect("Reference Applicazione", ra_opts)
    df_app_view = df_app_basic
    if sel_ba:
        df_app_view = df_app_view[df_app_view['company_name'].isin(sel_ba)]
    if sel_ra:
        df_app_view = df_app_view[df_app_view['relation_code'].isin(sel_ra)]
    st.dataframe(df_app_view.reset_index(drop=True), use_container_width=True)

# Footer
st.markdown("---")
st.write("© 2025 Dashboard Prodotti & Applicazioni")
