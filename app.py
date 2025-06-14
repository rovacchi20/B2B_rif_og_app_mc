import streamlit as st
import pandas as pd

# -------------------------------------------
# Configurazione pagina
# -------------------------------------------
st.set_page_config(page_title="Dashboard Prodotti & Applicazioni & SAP", layout="wide")

# -------------------------------------------
# Sidebar: upload file
# -------------------------------------------
with st.sidebar:
    st.markdown("## 📥 Carica i file Excel")
    prod_file = st.file_uploader("Dati Prodotti B2B", type=["xlsx","xls"])
    rif_file = st.file_uploader("Riferimenti Originali", type=["xlsx","xls"])
    app_file = st.file_uploader("Applicazioni Macchine", type=["xlsx","xls"])
    st.markdown("## 📤 Carica File Dati SAP")
    sap_file = st.file_uploader("Excel Dati SAP", type=["xlsx","xls"])

if not (prod_file and rif_file and app_file):
    st.sidebar.warning("Carica tutti e tre i file per procedere.")
    st.stop()

# -------------------------------------------
# Utility per normalizzare colonne
# -------------------------------------------
def normalize_columns(df):
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(' ', '_')
                  .str.replace('[^0-9a-zA-Z_]', '', regex=True)
    )
    return df

def find_column(columns, possible_names):
    for name in possible_names:
        for col in columns:
            if col.replace('_', '').lower() == name.replace('_', '').lower():
                return col
    return None

@st.cache_data
def load_excel(file):
    df = pd.read_excel(file, dtype=str)
    return normalize_columns(df)

# -------------------------------------------
# Lettura file Excel
# -------------------------------------------
df_prod = load_excel(prod_file)
df_rif = load_excel(rif_file)
df_app = load_excel(app_file)
df_sap = load_excel(sap_file) if sap_file else None

# -------------------------------------------
# Tabs
# -------------------------------------------
t1, t2, t3, t4, t5 = st.tabs([
    "B2B",
    "Riferimenti",
    "Applicazioni",
    "Dati SAP",
    "Esplosi B2B Viewer"   # ← nuovo tab
])

# ---- TAB B2B ----
with t1:
    st.markdown("### Dashboard Prodotti B2B")
    # Verifica colonne fondamentali
    if not all(col in df_prod.columns for col in ["product_code", "category_text"]):
        st.warning(
            "Colonne fondamentali mancanti nel file B2B: servono 'product_code' e 'category_text'."
        )
        st.write("Colonne trovate:", df_prod.columns.tolist())
    else:
        # Filtri
        df_basic = df_prod[["product_code", "category_text"]].copy()
        categories = sorted(df_basic['category_text'].dropna().unique())
        skus_all = sorted(df_basic['product_code'].dropna().unique())

        col1, col2 = st.columns(2)
        with col1:
            sel_cat = st.selectbox("Category Text", [""] + categories)
        with col2:
            skus = (
                sorted(df_basic[df_basic['category_text']==sel_cat]['product_code'].dropna().unique())
                if sel_cat else skus_all
            )
            sel_sku = st.selectbox("Filtra per SKU", [""] + skus)

        # Visualizzazione avanzata solo se selezionato
        if sel_cat or sel_sku:
            df_view = df_prod.copy()
            if sel_cat:
                df_view = df_view[df_view['category_text'] == sel_cat]
            if sel_sku:
                df_view = df_view[df_view['product_code'] == sel_sku]

            # ---- Merge riferimenti come da originale ----
            df_rif_full = df_rif.copy()
            if 'code' in df_rif_full.columns:
                company_name_col = find_column(
                    df_rif_full.columns,
                    ['company_name', 'brand']
                )
                relation_code_col = find_column(
                    df_rif_full.columns,
                    ['relation_code', 'reference', 'riferimento_originale']
                )
                if company_name_col and relation_code_col:
                    temp = df_rif_full[
                        df_rif_full['code'].isin(
                            df_view['product_code'].str.lstrip('0')
                        )
                    ].copy()
                    temp['idx'] = temp.groupby('code').cumcount() + 1

                    piv = temp.pivot(
                        index='code',
                        columns='idx',
                        values=[company_name_col, relation_code_col]
                    )
                    piv.columns = [
                        f"brand{i}" if col == company_name_col else f"reference{i}"
                        for col, i in piv.columns
                    ]
                    piv = piv.reset_index().rename(columns={'code':'sku'})
                    piv['sku_stripped'] = piv['sku'].str.lstrip('0')

                    df_view['prod_stripped'] = df_view['product_code'].str.lstrip('0')
                    merged = df_view.merge(
                        piv,
                        left_on='prod_stripped',
                        right_on='sku_stripped',
                        how='left'
                    )
                else:
                    merged = df_view.copy()
            else:
                merged = df_view.copy()

            # ---- Multiselect colonne ----
            available = [c for c in merged.columns if merged[c].notna().any()]
            sel_cols = st.multiselect("Colonne da mostrare", available, default=available)
            if sel_cols:
                st.dataframe(merged[sel_cols].reset_index(drop=True), use_container_width=True)
            else:
                st.info("Seleziona almeno una categoria o uno SKU per caricare i dati.")


# ---- TAB RIFERIMENTI ----
with t2:
    st.markdown("### Riferimenti Originali")
    show_df = df_rif.copy()
    if "marca" in show_df.columns:
        show_df = show_df.drop(columns=["codice_marca"])
    code_opts = sorted(show_df['code'].dropna().unique()) if 'code' in show_df.columns else []
    marca_opts = sorted(show_df['marca'].dropna().unique()) if 'marca' in show_df.columns else []
    rif_orig_opts = sorted(show_df['riferimento_originale'].dropna().unique()) if 'riferimento_originale' in show_df.columns else []

    sel_code = st.multiselect("Code", code_opts)
    sel_marca = st.multiselect("Marca", marca_opts)
    sel_rif_orig = st.multiselect("Riferimento originale", rif_orig_opts)

    df_view = show_df
    if sel_code:
        df_view = df_view[df_view['code'].isin(sel_code)]
    if sel_marca:
        df_view = df_view[df_view['marca'].isin(sel_marca)]
    if sel_rif_orig:
        df_view = df_view[df_view['riferimento_originale'].isin(sel_rif_orig)]
    st.dataframe(df_view.reset_index(drop=True), use_container_width=True)

# ---- TAB APPLICAZIONI ----
with t3:
    st.markdown("### Applicazioni Macchine")
    show_df = df_app.copy()
    if "marca" in show_df.columns:
        show_df = show_df.drop(columns=["codice_marca"])
    code_opts = sorted(show_df['code'].dropna().unique()) if 'code' in show_df.columns else []
    marca_opts = sorted(show_df['marca'].dropna().unique()) if 'marca' in show_df.columns else []
    modello_opts = sorted(show_df['modello'].dropna().unique()) if 'modello' in show_df.columns else []

    sel_code = st.multiselect("Code", code_opts)
    sel_marca = st.multiselect("Marca", marca_opts)
    sel_modello = st.multiselect("Modello", modello_opts)

    df_view = show_df
    if sel_code:
        df_view = df_view[df_view['code'].isin(sel_code)]
    if sel_marca:
        df_view = df_view[df_view['marca'].isin(sel_marca)]
    if sel_modello:
        df_view = df_view[df_view['modello'].isin(sel_modello)]
    st.dataframe(df_view.reset_index(drop=True), use_container_width=True)

# ---- TAB SAP ----
with t4:
    st.markdown("### Dati SAP")
    if df_sap is None:
        st.warning("Carica l'Excel Dati SAP nella tab Dati SAP per procedere.")
    else:
        show_df = df_sap.copy()
        if "marca" in show_df.columns:
            show_df = show_df.drop(columns=["marca"])
        materialcode_col = find_column(show_df.columns, ['materialcode', 'material_code'])
        if materialcode_col:
            material_opts = sorted(show_df[materialcode_col].dropna().unique())
            sel_material = st.multiselect("Materialcode", material_opts)
            df_view = show_df
            if sel_material:
                df_view = df_view[df_view[materialcode_col].isin(sel_material)]
            st.dataframe(df_view.reset_index(drop=True), use_container_width=True)
        else:
            st.warning(f"Nessuna colonna 'Materialcode' trovata nel file SAP. Colonne disponibili: {show_df.columns.tolist()}")

# ---- TAB ESplosi B2B VIEWER ----
with t5:
    uploaded_file = st.file_uploader(
        label="Carica il file Excel o CSV contenente i dati",
        type=["xlsx", "csv"],
        key="esplosi_b2b"   # chiave dedicata per evitare conflitti
    )
    if uploaded_file:
        # legge Excel o CSV a seconda dell’estensione
        df = (pd.read_excel(uploaded_file)
              if uploaded_file.name.endswith(".xlsx")
              else pd.read_csv(uploaded_file))

        # controlla che ci siano tutte le colonne necessarie
        required_columns = [
            "codice_ama",
            "titolo",
            "parent",
            "category_name",
            "link_url"
        ]
        if not set(required_columns).issubset(df.columns):
            st.error(f"Manca una colonna tra: {required_columns}")
            st.stop()

        st.subheader("Filtri")
        c1, c2, c3, c4 = st.columns(4)
        codes     = sorted(df["codice_ama"].dropna().astype(str).unique())
        titles    = sorted(df["titolo"].dropna().astype(str).unique())
        parents   = sorted(df["parent"].dropna().astype(str).unique())
        categories= sorted(df["category_name"].dropna().astype(str).unique())

        code_filter     = c1.selectbox("Filtra codice_ama:", ["Tutti"] + codes)
        title_filter    = c2.selectbox("Filtra titolo:",    ["Tutti"] + titles)
        parent_filter   = c3.selectbox("Filtra parent:",    ["Tutti"] + parents)
        category_filter = c4.selectbox("Filtra category_name:", ["Tutti"] + categories)

        dff = df.copy()
        if code_filter     != "Tutti": dff = dff[dff["codice_ama"]   == code_filter]
        if title_filter    != "Tutti": dff = dff[dff["titolo"]       == title_filter]
        if parent_filter   != "Tutti": dff = dff[dff["parent"]       == parent_filter]
        if category_filter != "Tutti": dff = dff[dff["category_name"]== category_filter]

        # crea la colonna HTML per il link
        dff["Link"] = dff["link_url"].apply(
            lambda u: f'<a href="{u}" target="_blank">Apri</a>'
        )
        display_cols = [
            "codice_ama",
            "titolo",
            "parent",
            "category_name",
            "Link"
        ]
        st.markdown(
            dff[display_cols]
               .to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
    else:
        st.info("Carica un file per iniziare.")

st.markdown("---")
st.write("© 2025 Dashboard Prodotti & Applicazioni & SAP")
