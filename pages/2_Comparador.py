# pages/2_Comparador.py
import streamlit as st
import altair as alt
import numpy as np
from utils_data import load_df, get_defaults, month_options, variable_catalog, label_to_code

st.set_page_config(page_title="Comparador", page_icon="🧭", layout="wide")
st.title("🧭 Comparador de variables")

df = load_df()
if df.empty:
    st.error("No hay datos.")
    st.stop()

st.sidebar.header("Filtros")
ent_default, var_default_label = get_defaults(df)
entidades = sorted(df["Entidad"].unique())
ent_sel = st.sidebar.selectbox("Entidad", options=entidades, index=(entidades.index(ent_default) if ent_default in entidades else 0))

cat = variable_catalog(df)
labs_all = cat["Var_label"].tolist()
preselect = [var_default_label] if var_default_label in labs_all else labs_all[:3]
vars_sel_labels = st.sidebar.multiselect("Variables (código – descripción)", options=labs_all, default=preselect)
vars_sel_codes = [label_to_code(df, lab) for lab in vars_sel_labels]

months = month_options(df)
rango = st.sidebar.select_slider("Rango de meses", options=months, value=(months[0], months[-1]))
m_min, m_max = rango

normalizar = st.sidebar.checkbox("Base 100 (primer mes del rango)", value=False)
yoy = st.sidebar.checkbox("Variación YoY (%)", value=False)

mask = (df["Entidad"] == ent_sel) & (df["Var_code"].isin(vars_sel_codes)) & (df["Mes"] >= m_min) & (df["Mes"] <= m_max)
dfv = df.loc[mask, ["Fecha_dt", "Mes", "Var_label", "Valor_num"]].copy()

if dfv.empty:
    st.warning("No hay datos para ese filtro.")
    st.stop()

if normalizar:
    base = dfv.groupby("Var_label")["Valor_num"].transform("first")
    dfv["Valor_calc"] = (dfv["Valor_num"] / base) * 100.0
    y_axis_title = "Índice (Base=100)"
elif yoy:
    dfv = dfv.sort_values("Fecha_dt").copy()
    dfv["Valor_calc"] = dfv.groupby("Var_label")["Valor_num"].transform(lambda s: s.pct_change(12) * 100.0)
    y_axis_title = "YoY (%)"
else:
    dfv["Valor_calc"] = dfv["Valor_num"]
    y_axis_title = "Valor"

chart = (
    alt.Chart(dfv.dropna(subset=["Valor_calc"]), height=420)
    .mark_line(point=True)
    .encode(
        x=alt.X("Fecha_dt:T", title="Mes"),
        y=alt.Y("Valor_calc:Q", title=y_axis_title),
        color=alt.Color("Var_label:N", title="Variable"),
        tooltip=[
            alt.Tooltip("Mes:N"),
            alt.Tooltip("Var_label:N", title="Variable"),
            alt.Tooltip("Valor_calc:Q", title=y_axis_title, format=",.2f"),
        ],
    )
)
st.altair_chart(chart, use_container_width=True)

st.caption("Tabla de datos")
st.dataframe(
    dfv.sort_values(["Var_label", "Fecha_dt"]).rename(columns={"Valor_calc": y_axis_title}),
    use_container_width=True,
)
