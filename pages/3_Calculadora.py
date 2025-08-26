# pages/3_Calculadora.py
import streamlit as st
import altair as alt
import numpy as np
import pandas as pd
from utils_data import load_df, get_defaults, month_options

st.set_page_config(page_title="Calculadora", page_icon="🧮", layout="wide")
st.title("🧮 Calculadora entre variables")

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
var_a = st.sidebar.selectbox("Variable A", options=vars_all, index=(vars_all.index(var_default) if var_default in vars_all else 0))
var_b = st.sidebar.selectbox("Variable B", options=vars_all, index=(vars_all.index(var_default) if var_default in vars_all else 0))

op = st.sidebar.selectbox("Operación", options=["A + B", "A - B", "A × B", "A ÷ B"], index=3)
months = month_options(df)
rango = st.sidebar.select_slider("Rango de meses", options=months, value=(months[0], months[-1]))
m_min, m_max = rango

# Datos
def get_series(code):
    m = (df["Entidad"] == ent_sel) & (df["Código del dato"] == code) & (df["Mes"] >= m_min) & (df["Mes"] <= m_max)
    s = df.loc[m, ["Fecha_dt", "Mes", "Valor_num"]].copy()
    return s.set_index("Fecha_dt").sort_index()

sa = get_series(var_a)
sb = get_series(var_b)
base = sa.join(sb, how="outer", lsuffix="_A", rsuffix="_B")

# Calcular
if op == "A + B":
    base["Resultado"] = base["Valor_num_A"] + base["Valor_num_B"]
elif op == "A - B":
    base["Resultado"] = base["Valor_num_A"] - base["Valor_num_B"]
elif op == "A × B":
    base["Resultado"] = base["Valor_num_A"] * base["Valor_num_B"]
else:
    # división segura
    denom = base["Valor_num_B"].replace(0, np.nan)
    base["Resultado"] = base["Valor_num_A"] / denom

# Chart
plot = base.reset_index().rename(columns={"index": "Fecha_dt"})
plot["Mes"] = plot["Fecha_dt"].dt.strftime("%Y-%m")
chart = (
    alt.Chart(plot.dropna(subset=["Resultado"]), height=420)
    .mark_line(point=True)
    .encode(
        x=alt.X("Fecha_dt:T", title="Mes"),
        y=alt.Y("Resultado:Q", title=f"Resultado ({op})"),
        tooltip=[
            alt.Tooltip("Mes:N"),
            alt.Tooltip("Resultado:Q", format=",.4f"),
        ],
    )
)
st.altair_chart(chart, use_container_width=True)

st.caption("Tabla de datos")
out = plot[["Mes", "Valor_num_A", "Valor_num_B", "Resultado"]].rename(
    columns={"Valor_num_A": var_a, "Valor_num_B": var_b}
)
st.dataframe(out, use_container_width=True)
