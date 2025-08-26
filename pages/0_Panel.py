# pages/0_Panel.py
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils_data import load_df, get_defaults, month_options, variable_catalog, label_to_code

st.set_page_config(page_title="Panel", page_icon="🧩", layout="wide")
st.title("🧩 Panel – KPIs por entidad")

df = load_df()
if df.empty:
    st.error("No hay datos en ./data/.")
    st.stop()

st.sidebar.header("Filtros")
ent_default, var_default_label = get_defaults(df)

entidades = sorted(df["Entidad"].unique())
idx_ent = entidades.index(ent_default) if ent_default in entidades else 0
ent_sel = st.sidebar.selectbox("Entidad", options=entidades, index=idx_ent)

months = month_options(df)
m_last = months[-1] if months else None
mes_sel = st.sidebar.select_slider("Mes", options=months, value=m_last)

# Variables a mostrar
cat = variable_catalog(df)
preselect = []
if var_default_label and var_default_label in cat["Var_label"].values:
    preselect = [var_default_label]
preselect = (preselect + cat["Var_label"].tolist())[:6]
vars_sel_labels = st.sidebar.multiselect(
    "Variables a mostrar (máx 8)", options=cat["Var_label"].tolist(), default=preselect, max_selections=8
)
vars_sel_codes = [label_to_code(df, lab) for lab in vars_sel_labels]

# Ventana temporal (para YoY/MoM)
def to_period(s):
    y, m = s.split("-")
    return pd.Period(year=int(y), month=int(m), freq="M")
p_obj = to_period(mes_sel)
p_prev = p_obj - 1
p_yoy = p_obj - 12

# Subset entidad + catálogo variables elegido
df_ent = df[(df["Entidad"] == ent_sel) & (df["Var_code"].isin(vars_sel_codes))].copy()
if df_ent.empty:
    st.warning("No hay datos para esos filtros.")
    st.stop()

df_ent["Period"] = df_ent["Fecha_dt"].dt.to_period("M")
pvt = df_ent.pivot_table(index="Var_label", columns="Period", values="Valor_num", aggfunc="last")

for p in [p_obj, p_prev, p_yoy]:
    if p not in pvt.columns:
        pvt[p] = np.nan

res = pd.DataFrame({
    "Variable": pvt.index,
    "Valor": pvt[p_obj],
    "MoM %": ((pvt[p_obj] / pvt[p_prev]) - 1.0) * 100.0,
    "YoY %": ((pvt[p_obj] / pvt[p_yoy]) - 1.0) * 100.0,
}).reset_index(drop=True)

res = res.sort_values(by=["Valor"], ascending=False)

c1, c2, c3 = st.columns([2,1,1])
with c1:
    st.subheader(f"{ent_sel}")
with c2:
    st.metric("Mes", mes_sel)
with c3:
    st.metric("Variables", f"{len(vars_sel_labels)} seleccionadas")

def fmt(v, nd=2):
    if pd.isna(v):
        return "—"
    try:
        return f"{float(v):,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)

cards_per_row = 4 if len(res) >= 4 else max(1, len(res))
rows = (len(res) + cards_per_row - 1) // cards_per_row
rows = min(rows, 4)

k = 0
for _ in range(rows):
    cols = st.columns(cards_per_row)
    for col in cols:
        if k >= len(res):
            break
        row = res.iloc[k]
        col.markdown(f"**{row['Variable']}**")
        col.metric(
            label="Valor",
            value=fmt(row["Valor"]),
            delta=f"{fmt(row['MoM %'],1)}% MoM" if not pd.isna(row["MoM %"]) else "—",
            help=f"YoY: {fmt(row['YoY %'],1)}%"
        )
        k += 1

st.markdown("### 📋 Detalle")
tabla = res.rename(columns={"Variable":"Código – Descripción"}).copy()
tabla["Valor"] = tabla["Valor"].map(fmt)
tabla["MoM %"] = tabla["MoM %"].map(lambda x: "—" if pd.isna(x) else f"{fmt(x,1)}%")
tabla["YoY %"] = tabla["YoY %"].map(lambda x: "—" if pd.isna(x) else f"{fmt(x,1)}%")
st.dataframe(tabla, use_container_width=True, hide_index=True)

st.markdown("### 📈 Minigráficos (24 meses)")
min_period = p_obj - 24
hist = df_ent[df_ent["Fecha_dt"].dt.to_period("M") >= min_period][["Fecha_dt","Var_label","Valor_num"]].copy()
if not hist.empty:
    chart = (
        alt.Chart(hist, height=320)
        .mark_line(point=True)
        .encode(
            x=alt.X("Fecha_dt:T", title="Mes"),
            y=alt.Y("Valor_num:Q", title="Valor"),
            color=alt.Color("Var_label:N", title="Variable"),
            tooltip=[
                alt.Tooltip("yearmonth(Fecha_dt):T", title="Mes"),
                alt.Tooltip("Var_label:N", title="Variable"),
                alt.Tooltip("Valor_num:Q", title="Valor", format=",.2f"),
            ],
        )
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No hay historial suficiente para graficar.")

st.download_button(
    label="⬇️ Descargar tabla del panel (CSV)",
    data=res.to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name=f"panel_{ent_sel.replace(' ','_')}_{mes_sel}.csv",
    mime="text/csv",
)
