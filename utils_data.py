# utils_data.py
from pathlib import Path
import re
import pandas as pd
import numpy as np
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

# Estructura esperada en cada CSV
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
    # coma decimal vs punto
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

def _read_csv_flexible(path: Path) -> pd.DataFrame:
    tries = [
        {"sep": ";", "enc": "utf-8-sig"},
        {"sep": ";", "enc": "latin-1"},
        {"sep": ",", "enc": "utf-8-sig"},
        {"sep": ",", "enc": "latin-1"},
        {"sep": "\t", "enc": "utf-8-sig"},
        {"sep": "\t", "enc": "latin-1"},
    ]
    last_err = None
    for t in tries:
        try:
            df = pd.read_csv(path, sep=t["sep"], encoding=t["enc"], dtype=str, engine="python")
            return df
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"No pude leer {path.name}: {last_err}")

@st.cache_data(show_spinner=True, ttl=600)
def load_df() -> pd.DataFrame:
    """
    Lee TODOS los .csv en ./data que contengan las columnas requeridas.
    Une, normaliza y devuelve un único DataFrame listo para usar.
    """
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    loaded_files = []
    for p in sorted(DATA_DIR.glob("*.csv")):
        try:
            df = _read_csv_flexible(p)
            missing = [c for c in COLS if c not in df.columns]
            if missing:
                # saltar archivos que no son de esta estructura
                continue
            df = df[COLS].copy()
            df["__archivo__"] = p.name  # solo informativo (no se usa para filtrar)
            frames.append(df)
            loaded_files.append(p.name)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame(columns=COLS + ["Fecha_dt", "Mes", "Valor_num", "Entidad", "Var_code", "Var_desc", "Var_label"])

    big = pd.concat(frames, ignore_index=True)

    # Normalizaciones
    big["Código de entidad"] = big["Código de entidad"].astype(str).str.strip().str.zfill(5)
    big["Descripción entidad"] = big["Descripción entidad"].astype(str).str.strip()

    dt, lab = zip(*big["Fecha del dato"].astype(str).map(_yyyymm_to_date))
    big["Fecha_dt"] = list(dt)
    big["Mes"] = list(lab)
    big = big.dropna(subset=["Fecha_dt"])

    big["Valor_num"] = big["Valor"].map(_to_float)
    big["Entidad"] = big["Código de entidad"] + " - " + big["Descripción entidad"].fillna("")

    # Variables (código + descripción para mostrar en UI)
    big["Var_code"] = big["Código del dato"].astype(str).str.strip()
    big["Var_desc"] = big["Descripción del dato"].astype(str).str.strip()
    # etiqueta amigable; si no hay desc, queda solo el código
    big["Var_label"] = np.where(
        big["Var_desc"].eq("") | big["Var_desc"].isna(),
        big["Var_code"],
        big["Var_code"] + " – " + big["Var_desc"]
    )

    big = big.sort_values(["Fecha_dt", "Código de entidad", "Var_code"]).reset_index(drop=True)

    # Info al usuario
    st.caption(
        f"Archivos cargados desde ./data: {len(loaded_files)} "
        + ("(" + ", ".join(loaded_files) + ")" if loaded_files else "")
    )

    return big

def get_defaults(df: pd.DataFrame):
    """Entidad: la que contenga 'nación' si existe; Variable: la que tenga código R1 si existe (por etiqueta)."""
    ent_default = None
    if not df.empty:
        ents = df["Entidad"].unique().tolist()
        cand = [e for e in ents if "nacion" in e.lower() or "nación" in e.lower()]
        ent_default = cand[0] if cand else (ents[0] if ents else None)

    var_default_label = None
    if not df.empty:
        # buscar etiqueta que empiece con "R1 "
        labs = df["Var_label"].unique().tolist()
        cand = [l for l in labs if l.startswith("R1 ")] or [l for l in labs if l.startswith("R1")]
        var_default_label = cand[0] if cand else (labs[0] if labs else None)

    return ent_default, var_default_label

def month_options(df: pd.DataFrame):
    months = df.dropna(subset=["Mes"])["Mes"].unique().tolist()
    months = sorted(months)
    return months

def variable_catalog(df: pd.DataFrame) -> pd.DataFrame:
    """Catálogo único de variables con código, descripción y etiqueta."""
    cat = df[["Var_code", "Var_desc", "Var_label"]].drop_duplicates().sort_values("Var_label")
    return cat

def label_to_code(df: pd.DataFrame, label: str) -> str:
    """Convierte etiqueta 'COD – Desc' a código 'COD' (si no encuentra, devuelve label)."""
    cat = variable_catalog(df)
    row = cat.loc[cat["Var_label"] == label]
    if not row.empty:
        return row.iloc[0]["Var_code"]
    # fallback: intentar cortar por ' – '
    if " – " in label:
        return label.split(" – ", 1)[0]
    return label
