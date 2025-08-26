# utils_data.py
from pathlib import Path
import re
import pandas as pd
import numpy as np
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
    s = s.replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    s = s.replace("%", "")
    try:
        return float(s)
    except Exception:
        return np.nan

def _yyyymm_to_date(yyyymm: str):
    if not isinstance(yyyymm, str):
        yyyymm = str(yyyymm)
    m = re.match(r"^\s*(\d{4})(\d{2})\s*$", yyyymm)
    if not m:
        return pd.NaT, None
    y, mth = int(m.group(1)), int(m.group(2))
    ts = pd.Timestamp(year=y, month=mth, day=1)
    return ts, f"{y:04d}-{mth:02d}"

def _read_csv_robusto(path: Path) -> pd.DataFrame:
    tries = [
        {"sep":";","enc":"utf-8-sig"},
        {"sep":";","enc":"latin-1"},
        {"sep":",","enc":"utf-8-sig"},
        {"sep":",","enc":"latin-1"},
        {"sep":"\t","enc":"utf-8-sig"},
        {"sep":"\t","enc":"latin-1"},
    ]
    last = None
    for t in tries:
        try:
            df = pd.read_csv(path, sep=t["sep"], encoding=t["enc"], dtype=str)
            return df
        except Exception as e:
            last = e
            continue
    raise RuntimeError(f"No pude leer {path.name}: {last}")

@st.cache_data(show_spinner=True, ttl=600)
def load_df() -> pd.DataFrame:
    """Lee TODOS los .csv en ./data/, valida columnas, concatena, normaliza y devuelve el DataFrame único."""
    if not DATA_DIR.exists():
        return pd.DataFrame(columns=COLS + ["Fecha_dt","Mes","Valor_num","Entidad"])

    frames = []
    for path in sorted(DATA_DIR.glob("*.csv")):
        # ignorar archivos 'ocultos' o vacíos
        if path.name.startswith("~$"):
            continue
        try:
            df = _read_csv_robusto(path)
            missing = [c for c in COLS if c not in df.columns]
            if missing:
                # si no tiene las columnas esperadas, lo saltamos silenciosamente
                continue
            df = df[COLS].copy()
            frames.append(df)
        except Exception:
            # si algún archivo falla, seguimos con los demás
            continue

    if not frames:
        return pd.DataFrame(columns=COLS + ["Fecha_dt","Mes","Valor_num","Entidad"])

    big = pd.concat(frames, ignore_index=True)

    # Normalizaciones
    big["Código de entidad"] = big["Código de entidad"].astype(str).str.strip().str.zfill(5)
    big["Descripción entidad"] = big["Descripción entidad"].astype(str).str.strip()
    big["Código del dato"] = big["Código del dato"].astype(str).str.strip()
    big["Descripción del dato"] = big["Descripción del dato"].astype(str).str.strip()

    dt, lab = zip(*big["Fecha del dato"].astype(str).map(_yyyymm_to_date))
    big["Fecha_dt"] = list(dt)
    big["Mes"] = list(lab)
    big = big.dropna(subset=["Fecha_dt"])

    big["Valor_num"] = big["Valor"].map(_to_float)
    big["Entidad"] = big["Código de entidad"] + " - " + big["Descripción entidad"].fillna("")

    # Quitar duplicados exactos por seguridad
    big = big.drop_duplicates()

    # Orden canónico
    big = big.sort_values(["Fecha_dt","Código de entidad","Código del dato"]).reset_index(drop=True)

    return big

def get_defaults(df: pd.DataFrame):
    """Defaults: entidad con 'nación' si existe, y variable código R1 si existe."""
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
    months = df.dropna(subset=["Mes"])["Mes"].unique().tolist()
    months = sorted(months)
    return months
