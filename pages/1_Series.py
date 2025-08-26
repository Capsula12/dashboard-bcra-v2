# pages/1_Series.py
import streamlit as st
import altair as alt
from utils_data import load_df, get_defaults, month_options, variable_catalog, label_to_code

st.set_page_config(page_title="Series", page_icon="📈", layout="wide")
st.title("📈 Series por variable")

df = load_df()
if df.empty:
    st.error("No hay datos.")
    st.stop()

st.sidebar.header("Filtros")
ent_default, var_default_label = get_defaults(df)

entidades = sorted(df["Entidad"].unique())
ent_sel = st.sidebar.selectbox("Entidad", options=entidades, index=(entidades.index(ent_default) if ent_default in entidades else 0))

cat = variable_catalog(df)
var_label = st.sidebar.selectbox("Variable (código – descripción)", options=cat["Var_label"].tolist(),
                                 index=(cat["Var_label"].tolist().index(var_default_label) if var_default_label in cat["Var_label"].tolist() else 0))
var_code = label_to_code(df, var_label)

months = month_options(df)
rango = st.sidebar.select_slider("Rango de meses", options=months, value=(months[0], months[-1]))
m_min, m_max = rango

mask = (
    (df["Entidad"] == ent_sel) &
    (df["Var_code"] == var_code) &
    (df["Mes"] >= m_min) & (df["Mes"] <= m_max)
)
dfv = df.loc[mask, ["Fecha_dt", "Mes", "Entidad", "Var_label", "Valor_num"]].copy()

if dfv.empty:
    st.warning("No hay datos para ese filtro.")
    st.stop()

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
            alt.Tooltip("Var_label:N", title="Variable"),
            alt.Tooltip("Valor_num:Q", title="Valor", format=",.2f"),
        ],
    )
)
st.altair_chart(chart, use_container_width=True)

st.caption("Tabla de datos")
st.dataframe(
    dfv.sort_values(["Entidad", "Fecha_dt"]).rename(columns={"Valor_num": "Valor"}),
    use_container_width=True,
)
