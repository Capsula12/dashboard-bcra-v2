# pages/3_Calculadora.py
import streamlit as st
import altair as alt
import numpy as np
from utils_data import load_df, get_defaults, month_options, variable_catalog, label_to_code

st.set_page_config(page_title="Calculadora", page_icon="🧮", layout="wide")
st.title("🧮 Calculadora entre variables")

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
idx_def = labs_all.index(var_default_label) if var_default_label in labs_all else 0
var_a_label = st.sidebar.selectbox("Variable A (código – descripción)", options=labs_all, index=idx_def)
var_b_label = st.sidebar.selectbox("Variable B (código – descripción)", options=labs_all, index=idx_def)

var_a = label_to_code(df, var_a_label)
var_b = label_to_code(df, var_b_label)

op = st.sidebar.selectbox("Operación", options=["A + B", "A - B", "A × B", "A ÷ B"], index=3)

months = month_options(df)
rango = st.sidebar.select_slider("Rango de meses", options=months, value=(months[0], months[-1]))
m_min, m_max = rango

def get_series(code):
    m = (df["Entidad"] == ent_sel) & (df["Var_code"] == code) & (df["Mes"] >= m_min) & (df["Mes"] <= m_max)
    s = df.loc[m, ["Fecha_dt", "Mes", "Valor_num"]].copy()
    return s.set_index("Fecha_dt").sort_index()

sa = get_series(var_a)
sb = get_series(var_b)
base = sa.join(sb, how="outer", lsuffix="_A", rsuffix="_B")

if op == "A + B":
    base["Resultado"] = base["Valor_num_A"] + base["Valor_num_B"]
elif op == "A - B":
    base["Resultado"] = base["Valor_num_A"] - base["Valor_num_B"]
elif op == "A × B":
    base["Resultado"] = base["Valor_num_A"] * base["Valor_num_B"]
else:
    denom = base["Valor_num_B"].replace(0, np.nan)
    base["Resultado"] = base["Valor_num_A"] / denom

plot = base.reset_index().rename(columns={"index": "Fecha_dt"})
plot["Mes"] = plot["Fecha_dt"].dt.strftime("%Y-%m")
chart = (
    alt.Chart(plot.dropna(subset=["Resultado"]), height=420)
    .mark_line(point=True)
    .encode(
        x=alt.X("Fecha_dt:T", title="Mes"),
        y=alt.Y("Resultado:Q", title=f"Resultado ({op})"),
        tooltip=[alt.Tooltip("Mes:N"), alt.Tooltip("Resultado:Q", format=",.4f")],
    )
)
st.altair_chart(chart, use_container_width=True)

st.caption("Tabla de datos")
out = plot[["Mes", "Valor_num_A", "Valor_num_B", "Resultado"]].rename(
    columns={"Valor_num_A": var_a_label, "Valor_num_B": var_b_label}
)
st.dataframe(out, use_container_width=True)
