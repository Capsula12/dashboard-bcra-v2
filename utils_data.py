# utils_data.py
from pathlib import Path
import pandas as pd
import numpy as np
import re
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

COLS = [
    "Código de entidad",
    "Descripción entidad",
    "Fecha del dato",
    "Código del dato",
    "Descripción del dato",
    "Valor",
]

def _to_float(v: str):
    if v is None:
        return np.nan
    s = str(v).strip()
    if s == "":
        return np.nan
    # Heurística robusta: quita separadores de miles y usa '.' como decimal
    s = s.replace(" ", "")
    # Si hay coma, asumimos que es decimal y removemos puntos
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    # Permití % al final
    s = s.replace("%", "")
    try:
        return float(s)
    except Exception:
        return np.nan

def _yyyymm_to_date(yyyymm: str):
    # Devuelve un timestamp (primer día del mes) y una etiqueta "YYYY-MM"
    if not isinstance(yyyymm, str):
        yyyymm = str(yyyymm)
    m = re.match(r"^\s*(\d{4})(\d{2})\s*$", yyyymm)
    if not m:
        return pd.NaT, None
    y, mth = int(m.group(1)), int(m.group(2))
    ts = pd.Timestamp(year=y, month=mth, day=1)
    return ts, f"{y:04d}-{mth:02d}"

@st.cache_data(show_spinner=False)
def load_df() -> pd.DataFrame:
    """Carga ambos CSV desde ./data y los unifica con columna 'Origen'."""
    frames = []
    files = [
        (DATA_DIR / "INF_ADI_FULL.csv", "INF_ADI"),
        (DATA_DIR / "INDICAD_FULL.csv", "INDICAD"),
    ]
    for path, origen in files:
        if not path.exists():
            continue
        df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
        # mantener solo columnas esperadas si hay extras
        missing = [c for c in COLS if c not in df.columns]
        if missing:
            raise ValueError(f"Faltan columnas {missing} en {path.name}")
        df = df[COLS].copy()
        df["Origen"] = origen
        frames.append(df)

    if not frames:
        return pd.DataFrame(columns=COLS + ["Origen"])

    big = pd.concat(frames, ignore_index=True)

    # Normalizaciones
    big["Código de entidad"] = big["Código de entidad"].astype(str).str.strip().str.zfill(5)
    big["Descripción entidad"] = big["Descripción entidad"].astype(str).str.strip()

    # Fecha
    dt, lab = zip(*big["Fecha del dato"].astype(str).map(_yyyymm_to_date))
    big["Fecha_dt"] = list(dt)
    big["Mes"] = list(lab)
    big = big.dropna(subset=["Fecha_dt"])
    big = big.sort_values(["Fecha_dt", "Código de entidad", "Código del dato"]).reset_index(drop=True)

    # Valor numérico
    big["Valor_num"] = big["Valor"].map(_to_float)

    # Etiqueta entidad
    big["Entidad"] = big["Código de entidad"] + " - " + big["Descripción entidad"].fillna("")

    return big

def get_defaults(df: pd.DataFrame):
    """Defaults: entidad que contenga 'nación' y código 'R1' si existen."""
    ent_default = None
    if not df.empty:
        ents = df["Entidad"].unique().tolist()
        cand = [e for e in ents if "nacion" in e.lower() or "nación" in e.lower()]
        ent_default = cand[0] if cand else (ents[0] if ents else None)

    var_default = None
    if not df.empty:
        vars_ = df["Código del dato"].unique().tolist()
        var_default = "R1" if "R1" in vars_ else (vars_[0] if vars_ else None)

    return ent_default, var_default

def month_options(df: pd.DataFrame):
    """Lista ordenada de etiquetas 'YYYY-MM' disponibles."""
    months = df.dropna(subset=["Mes"])["Mes"].unique().tolist()
    months = sorted(months)
    return months
