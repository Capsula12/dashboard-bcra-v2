# pages/0_Panel.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils_data import load_df, get_defaults, month_options

st.set_page_config(page_title="Panel", page_icon="🧩", layout="wide")
st.title("🧩 Panel – KPIs por entidad")

df = load_df()
if df.empty:
    st.error("No hay datos en ./data (INF_ADI_FULL.csv / INDICAD_FULL.csv).")
    st.stop()

# ------------------ Sidebar: filtros ------------------
st.sidebar.header("Filtros")
origenes = sorted(df["Origen"].unique())
origen_sel = st.sidebar.multiselect("Origen", origenes, default=origenes)
df = df[df["Origen"].isin(origen_sel)]
if df.empty:
    st.warning("Sin datos para los orígenes seleccionados.")
    st.stop()

ent_default, _var_default = get_defaults(df)
entidades = sorted(df["Entidad"].unique())
idx_ent = entidades.index(ent_default) if ent_default in entidades else 0
ent_sel = st.sidebar.selectbox("Entidad", options=entidades, index=idx_ent)

months = month_options(df)
m_last = months[-1] if months else None
rango_mes = st.sidebar.select_slider("Mes", options=months, value=m_last)

# cantidad de KPIs a mostrar y preselección
st.sidebar.markdown("---")
vars_all = sorted(df["Código del dato"].unique())
# preselección "inteligente": si existen estos códigos, van primero
prefer = ["R1", "R2", "R3", "R4", "R5"]
pref_found = [v for v in prefer if v in vars_all]
rest = [v for v in vars_all if v not in pref_found]
preselect = (pref_found + rest)[:6]
vars_sel = st.sidebar.multiselect("Variables a mostrar (máx 8)", options=vars_all, default=preselect, max_selections=8)

# ------------------ Preparación de datos ------------------
# Subset por entidad y rango de 13 meses para tener YoY
df_ent = df[df["Entidad"] == ent_sel].copy()
if df_ent.empty:
    st.warning("No hay datos para la entidad seleccionada.")
    st.stop()

# Determinar ventana temporal que cubra el mes elegido, el mes previo y el mismo mes -12
mes_obj = rango_mes
# convertir etiqueta "YYYY-MM" a periodo mensual
def to_period(s):
    y, m = s.split("-")
    return pd.Period(year=int(y), month=int(m), freq="M")

p_obj = to_period(mes_obj)
p_prev = p_obj - 1
p_yoy = p_obj - 12

# df con columna Period para joins
df_ent["Period"] = df_ent["Fecha_dt"].dt.to_period("M")
df_ent = df_ent[df_ent["Código del dato"].isin(vars_sel)]

if df_ent.empty:
    st.warning("No hay datos para las variables elegidas.")
    st.stop()

# Pivot en formato (variable x periodo) para cálculos
pvt = df_ent.pivot_table(
    index="Código del dato",
    columns="Period",
    values="Valor_num",
    aggfunc="last"
)

# Garantizar columnas necesarias
for p in [p_obj, p_prev, p_yoy]:
    if p not in pvt.columns:
        pvt[p] = np.nan

# DataFrame resumen KPI
res = pd.DataFrame({
    "Código del dato": pvt.index,
    "Valor": pvt[p_obj],
    "MoM %": ((pvt[p_obj] / pvt[p_prev]) - 1.0) * 100.0,
    "YoY %": ((pvt[p_obj] / pvt[p_yoy]) - 1.0) * 100.0,
}).reset_index(drop=True)

# Descripciones de variable
desc_map = df_ent.set_index("Código del dato")["Descripción del dato"].dropna().to_dict()
res["Descripción"] = res["Código del dato"].map(desc_map)

# Orden por valor absoluto (desc) para mostrar más “relevantes”
res = res.sort_values(by=["Valor"], ascending=False)

# ------------------ Encabezado ------------------
c1, c2, c3 = st.columns([2,1,1])
with c1:
    st.subheader(f"{ent_sel}")
with c2:
    st.metric("Mes", mes_obj)
with c3:
    st.metric("Variables", f"{len(vars_sel)} seleccionadas")

# ------------------ Tarjetas KPI ------------------
def fmt(v, nd=2):
    if pd.isna(v):
        return "—"
    try:
        return f"{float(v):,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)

# Mostrar en filas de 3/4 tarjetas
cards_per_row = 4 if len(res) >= 4 else max(1, len(res))
rows = (len(res) + cards_per_row - 1) // cards_per_row
rows = min(rows, 4)  # para no excesivo alto

k = 0
for _ in range(rows):
    cols = st.columns(cards_per_row)
    for col in cols:
        if k >= len(res):
            break
        row = res.iloc[k]
        title = f"{row['Código del dato']}"
        subtitle = row.get("Descripción") or ""
        col.markdown(f"**{title}**  \n<small>{subtitle}</small>", unsafe_allow_html=True)
        col.metric(
            label="Valor",
            value=fmt(row["Valor"]),
            delta=f"{fmt(row['MoM %'],1)}% MoM" if not pd.isna(row["MoM %"]) else "—",
            help=f"YoY: {fmt(row['YoY %'],1)}%"
        )
        k += 1

# ------------------ Ranking y tabla ------------------
st.markdown("### 📋 Detalle de variables")
rank_cols = ["Código del dato", "Descripción", "Valor", "MoM %", "YoY %"]
tabla = res[rank_cols].copy()
# formateo amigable
tabla["Valor"] = tabla["Valor"].map(fmt)
tabla["MoM %"] = tabla["MoM %"].map(lambda x: "—" if pd.isna(x) else f"{fmt(x,1)}%")
tabla["YoY %"] = tabla["YoY %"].map(lambda x: "—" if pd.isna(x) else f"{fmt(x,1)}%")
st.dataframe(tabla, use_container_width=True, hide_index=True)

# ------------------ Sparklines por variable ------------------
st.markdown("### 📈 Minigráficos por variable")
# Traemos 24 meses atrás para chispear
min_period = p_obj - 24
hist = df_ent[df_ent["Period"] >= min_period][["Fecha_dt","Period","Código del dato","Descripción del dato","Valor_num"]].copy()

if not hist.empty:
    # Chart combinado: una serie por variable seleccionada
    chart = (
        alt.Chart(hist, height=320)
        .mark_line()
        .encode(
            x=alt.X("Fecha_dt:T", title="Mes"),
            y=alt.Y("Valor_num:Q", title="Valor"),
            color=alt.Color("Código del dato:N", title="Variable"),
            tooltip=[
                alt.Tooltip("yearmonth(Fecha_dt):T", title="Mes"),
                alt.Tooltip("Código del dato:N", title="Código"),
                alt.Tooltip("Descripción del dato:N", title="Descripción"),
                alt.Tooltip("Valor_num:Q", title="Valor", format=",.2f"),
            ],
        )
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No hay historial suficiente para graficar.")

# ------------------ Descarga ------------------
st.download_button(
    label="⬇️ Descargar tabla del panel (CSV)",
    data=res.to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name=f"panel_{ent_sel.replace(' ','_')}_{mes_obj}.csv",
    mime="text/csv",
)
