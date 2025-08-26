# app.py
import streamlit as st
from utils_data import load_df

st.set_page_config(page_title="Indicadores BCRA – Dashboard", page_icon="📊", layout="wide")

st.title("Indicadores BCRA – Dashboard")
st.markdown(
    """
    Este tablero lee **dos archivos** desde `./data/`:
    - `INF_ADI_FULL.csv`
    - `INDICAD_FULL.csv`

    Cada archivo debe tener las columnas:  
    **Código de entidad · Descripción entidad · Fecha del dato (AAAAMM) · Código del dato · Descripción del dato · Valor**
    """
)

df = load_df()

if df.empty:
    st.error("No encontré datos. Verificá que `./data/INF_ADI_FULL.csv` y/o `./data/INDICAD_FULL.csv` existan y tengan el formato esperado.")
else:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Filas", f"{len(df):,}".replace(",", "."))
    with col2:
        st.metric("Entidades", df["Código de entidad"].nunique())
    with col3:
        st.metric("Variables", df["Código del dato"].nunique())
    with col4:
        origenes = ", ".join(sorted(df["Origen"].unique()))
        st.metric("Orígenes", origenes or "—")

    st.info("Usá el menú lateral **▶ Pages** para navegar: **Series**, **Comparador**, **Calculadora**.")
