# pages/2_Comparador.py
import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from utils_data import load_df, get_defaults, month_options

st.set_page_config(page_title="Comparador", page_icon="🧭", layout="wide")
st.title("🧭 Comparador de variables")

df = load_df()
if df.empty:
    st.error("No hay datos.")
    st.stop()

# Sidebar
st.sidebar.header("Filtros")
origenes = st.sidebar.multiselect("Origen", sorted(df["Origen"].unique()), default=sorted(df["Origen"].unique()))
df = df[df["Origen"].isin(origenes)]

ent_default, var_default = get_defaults(df)
ent_sel = st.sidebar.selectbox("Entidad", options=sorted(df["Entidad"].unique()), index=0 if not ent_default else sorted(df["Entidad"].unique()).index(ent_default))

vars_all = sorted(df["Código del dato"].unique())
preselect = [v for v in ["R1"] if v in vars_all] or vars_all[:3]
vars_sel = st.sidebar.multiselect("Variables", options=vars_all, default=preselect)

months = month_options(df)
rango = st.sidebar.select_slider("Rango de meses", options=months, value=(months[0], months[-1]))
m_min, m_max = rango

normalizar = st.sidebar.checkbox("Base 100 (primer mes del rango)", value=False)
yoy = st.sidebar.checkbox("Variación YoY (%)", value=False)

# Filtro
mask = (df["Entidad"] == ent_sel) & (df["Código del dato"].isin(vars_sel)) & (df["Mes"] >= m_min) & (df["Mes"] <= m_max)
dfv = df.loc[mask, ["Fecha_dt", "Mes", "Código del dato", "Descripción del dato", "Valor_num", "Origen"]].copy()

if dfv.empty:
    st.warning("No hay datos para ese filtro.")
    st.stop()

# Transformaciones
if normalizar:
    base = dfv.groupby("Código del dato")["Valor_num"].transform("first")
    dfv["Valor_calc"] = (dfv["Valor_num"] / base) * 100.0
    y_axis_title = "Índice (Base=100)"
elif yoy:
    # YoY por variable: usar 12 meses atrás
    dfv = dfv.sort_values("Fecha_dt").copy()
    dfv["Valor_calc"] = dfv.groupby("Código del dato")["Valor_num"].transform(lambda s: s.pct_change(12) * 100.0)
    y_axis_title = "YoY (%)"
else:
    dfv["Valor_calc"] = dfv["Valor_num"]
    y_axis_title = "Valor"

# Chart
chart = (
    alt.Chart(dfv.dropna(subset=["Valor_calc"]), height=420)
    .mark_line(point=True)
    .encode(
        x=alt.X("Fecha_dt:T", title="Mes"),
        y=alt.Y("Valor_calc:Q", title=y_axis_title),
        color=alt.Color("Código del dato:N", title="Variable"),
        tooltip=[
            alt.Tooltip("Mes:N"),
            alt.Tooltip("Código del dato:N", title="Código"),
            alt.Tooltip("Descripción del dato:N", title="Descripción"),
            alt.Tooltip("Valor_calc:Q", title=y_axis_title, format=",.2f"),
            alt.Tooltip("Origen:N"),
        ],
    )
)
st.altair_chart(chart, use_container_width=True)

st.caption("Tabla de datos")
st.dataframe(
    dfv.sort_values(["Código del dato", "Fecha_dt"]).rename(columns={"Valor_calc": y_axis_title}),
    use_container_width=True,
)
