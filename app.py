# app.py
import streamlit as st
from utils_data import load_df

st.set_page_config(page_title="Indicadores BCRA – Dashboard", page_icon="📊", layout="wide")

st.title("Indicadores BCRA – Dashboard")
st.markdown(
    """
    Este tablero lee **todos los CSV** ubicados en `./data/` que tengan columnas:  
    **Código de entidad · Descripción entidad · Fecha del dato (AAAAMM) · Código del dato · Descripción del dato · Valor**.

    Usá el menú lateral **▶ Pages** para navegar: **Panel**, **Series**, **Comparador**, **Calculadora**.
    """
)

df = load_df()

if df.empty:
    st.error("No encontré datos válidos en `./data/`.")
else:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filas", f"{len(df):,}".replace(",", "."))
    with col2:
        st.metric("Entidades", df["Código de entidad"].nunique())
    with col3:
        st.metric("Variables", df["Var_label"].nunique())
