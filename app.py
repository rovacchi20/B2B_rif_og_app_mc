import streamlit as st
import pandas as pd

# -------------------------------------------
# Configurazione pagina
# -------------------------------------------
st.set_page_config(page_title="Dashboard Prodotti & Applicazioni & SAP", layout="wide")
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
    st.markdown("## 📤 Carica File Dati SAP")
    sap_file = st.file_uploader("Excel Dati SAP", type=["xlsx","xls"])

if not (prod_file and ref_file and app_file):
    st.sidebar.warning("Carica tutti e tre i file per procedere.")
    st.stop()

# -------------------------------------------
# Caching data load per Prodotti & Riferimenti
# -------------------------------------------
@st.cache_data
def load_basic_products(f):
    f.seek(0)
    return pd.read_excel(f, usecols=["product_code","category_text"], dtype=str)

@st.cache_data
def load_basic_references(f):
    f.seek(0)
    return pd.read_excel(f, usecols=["code","company_name","relation_code"], dtype=str)

@st.cache_data
def load_basic_applications(f):
    f.seek(0)
    return pd.read_excel(f, usecols=["code","company_name","relation_code"], dtype=str)

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
# Utility per Dati SAP
# -------------------------------------------
@st.cache_data
def load_excel(file):
    df = pd.read_excel(file, dtype=str)
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(' ', '_')
                  .str.replace('[^0-9a-zA-Z_]', '', regex=True)
    )
    return df


def find_material_col(columns):
    for col in columns:
        if 'material' in col and 'code' in col:
            return col
    return None

# -------------------------------------------
# Setup iniziale dei filtri Prodotti
# -------------------------------------------
df_basic = load_basic_products(prod_file)
categories = sorted(df_basic['category_text'].dropna().unique())
skus_all = sorted(df_basic['product_code'].str.lstrip('0').dropna().unique())

col1, col2 = st.columns(2)
with col1:
    sel_cat = st.selectbox("Category Text", [""] + categories)
with col2:
    if sel_cat:
        skus = sorted(
            df_basic[df_basic['category_text']==sel_cat]['product_code']
                   .str.lstrip('0').dropna().unique()
        )
    else:
        skus = skus_all
    sel_sku = st.selectbox("Filtra per SKU", [""] + skus)

# -------------------------------------------
# Logica on-demand Prodotti
# -------------------------------------------
if sel_cat or sel_sku:
    df_prod_full = load_full_products(prod_file)
    df_view = df_prod_full
    if sel_cat:
        df_view = df_view[df_view['category_text']==sel_cat]
    if sel_sku:
        df_view = df_view[df_view['product_code'].str.lstrip('0')==sel_sku]

    df_ref_full = load_full_references(ref_file)
    temp = df_ref_full[df_ref_full['code'].isin(
        df_view['product_code'].str.lstrip('0')
    )].copy()
    temp['idx'] = temp.groupby('code').cumcount()+1
    piv = temp.pivot(index='code', columns='idx', values=['company_name','relation_code'])
    piv.columns = [f"brand{i}" if c=='company_name' else f"reference{i}" for c,i in piv.columns]
    piv = piv.reset_index().rename(columns={'code':'sku'})
    piv['sku_stripped'] = piv['sku'].str.lstrip('0')

    df_view['prod_stripped'] = df_view['product_code'].str.lstrip('0')
    merged = df_view.merge(
        piv, left_on='prod_stripped', right_on='sku_stripped', how='left'
    )

    available = [c for c in merged.columns if merged[c].notna().any()]
    sel_cols = st.multiselect("Colonne da mostrare", available, default=available)
    if sel_cols:
        st.dataframe(merged[sel_cols].reset_index(drop=True), use_container_width=True)
else:
    st.info("Seleziona almeno una categoria o uno SKU per caricare i dati.")

# -------------------------------------------
# Tab Riferimenti, Applicazioni e Dati SAP
# -------------------------------------------
t2, t3, t4 = st.tabs(["Riferimenti","Applicazioni","Dati SAP"])

with t2:
    df_ref_basic = load_basic_references(ref_file)
    b_opts = sorted(df_ref_basic['company_name'].dropna().unique())
    r_opts = sorted(df_ref_basic['relation_code'].dropna().unique())
    sel_br = st.multiselect("Brand", b_opts)
    sel_rr = st.multiselect("Reference", r_opts)
    code_opts = sorted(df_ref_basic['code'].dropna().unique())
    sel_code = st.multiselect("Code", code_opts)
    df_ref_view = df_ref_basic
    if sel_br:
        df_ref_view = df_ref_view[df_ref_view['company_name'].isin(sel_br)]
    if sel_rr:
        df_ref_view = df_ref_view[df_ref_view['relation_code'].isin(sel_rr)]
    if sel_code:
        df_ref_view = df_ref_view[df_ref_view['code'].isin(sel_code)]
    st.dataframe(df_ref_view.reset_index(drop=True), use_container_width=True)

with t3:
    df_app_basic = load_basic_applications(app_file)
    ba_opts = sorted(df_app_basic['company_name'].dropna().unique())
    ra_opts = sorted(df_app_basic['relation_code'].dropna().unique())
    sel_ba = st.multiselect("Brand Applicazione", ba_opts)
    sel_ra = st.multiselect("Reference Applicazione", ra_opts)
    app_code_opts = sorted(df_app_basic['code'].dropna().unique())
    sel_code_app = st.multiselect("Code", app_code_opts)
    df_app_view = df_app_basic
    if sel_ba:
        df_app_view = df_app_view[df_app_view['company_name'].isin(sel_ba)]
    if sel_ra:
        df_app_view = df_app_view[df_app_view['relation_code'].isin(sel_ra)]
    if sel_code_app:
        df_app_view = df_app_view[df_app_view['code'].isin(sel_code_app)]
    st.dataframe(df_app_view.reset_index(drop=True), use_container_width=True)

with t4:
    st.markdown("### Dashboard Dati SAP")
    if not sap_file:
        st.warning("Carica l'Excel Dati SAP nella tab Dati SAP per procedere.")
    else:
        df_sap = load_excel(sap_file)
        df_filtered = df_sap.copy()
        material_col = find_material_col(df_sap.columns)
        if material_col:
            mat_label = material_col.replace('_', ' ').title()
            mat_vals = df_sap[material_col].dropna().unique().tolist()
            sel_mat = st.multiselect(f"Filtra {mat_label}", options=sorted(mat_vals), key="filter_material_code")
            if sel_mat:
                df_filtered = df_filtered[df_filtered[material_col].isin(sel_mat)]
        for col in df_sap.columns:
            if col == material_col:
                continue
            vals = df_sap[col].dropna().unique().tolist()
            if 1 < len(vals) <= 100:
                label = col.replace('_', ' ').title()
                sel = st.multiselect(f"Filtra {label}", options=sorted(vals), key=f"filter_{col}")
                if sel:
                    df_filtered = df_filtered[df_filtered[col].isin(sel)]
        st.dataframe(df_filtered.reset_index(drop=True), use_container_width=True)

# Footer
st.markdown("---")
st.write("© 2025 Dashboard Prodotti & Applicazioni & SAP")
