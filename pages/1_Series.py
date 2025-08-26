# pages/1_Series.py
import streamlit as st
import altair as alt
import pandas as pd
from utils_data import load_df, get_defaults, month_options

st.set_page_config(page_title="Series", page_icon="📈", layout="wide")
st.title("📈 Series por variable")

df = load_df()
if df.empty:
    st.error("No hay datos.")
    st.stop()

# Sidebar
st.sidebar.header("Filtros")
origenes = st.sidebar.multiselect("Origen", sorted(df["Origen"].unique()), default=sorted(df["Origen"].unique()))
df = df[df["Origen"].isin(origenes)]

ent_default, var_default = get_defaults(df)

entidades = st.sidebar.multiselect("Entidades", sorted(df["Entidad"].unique()), default=[ent_default] if ent_default else [])
variables = sorted(df["Código del dato"].unique())
var_sel = st.sidebar.selectbox("Variable", options=variables, index=(variables.index(var_default) if var_default in variables else 0))

months = month_options(df)
if not months:
    st.error("No hay meses válidos (columna 'Fecha del dato').")
    st.stop()

rango = st.sidebar.select_slider("Rango de meses", options=months, value=(months[0], months[-1]))
m_min, m_max = rango

# Filtro principal
mask = (
    df["Entidad"].isin(entidades) &
    (df["Código del dato"] == var_sel) &
    (df["Mes"] >= m_min) & (df["Mes"] <= m_max)
)
dfv = df.loc[mask, ["Fecha_dt", "Mes", "Entidad", "Código del dato", "Descripción del dato", "Valor_num", "Origen"]].copy()

if dfv.empty:
    st.warning("No hay datos para ese filtro.")
    st.stop()

# Chart
chart = (
    alt.Chart(dfv, height=420)
    .mark_line(point=True)
    .encode(
        x=alt.X("Fecha_dt:T", title="Mes"),
        y=alt.Y("Valor_num:Q", title="Valor"),
        color=alt.Color("Entidad:N", title="Entidad"),
        tooltip=[
            alt.Tooltip("Mes:N"),
            alt.Tooltip("Entidad:N"),
            alt.Tooltip("Descripción del dato:N", title="Variable"),
            alt.Tooltip("Valor_num:Q", title="Valor", format=",.2f"),
            alt.Tooltip("Origen:N"),
        ],
    )
)

st.altair_chart(chart, use_container_width=True)

st.caption("Tabla de datos")
st.dataframe(
    dfv.sort_values(["Entidad", "Fecha_dt"]).rename(columns={"Valor_num": "Valor"}),
    use_container_width=True,
)
