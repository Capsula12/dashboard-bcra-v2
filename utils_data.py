# utils_data.py
from pathlib import Path
import re
import unicodedata
import pandas as pd
import numpy as np
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

# Estructura estándar del dashboard
COLS_STD = [
    "Código de entidad",
    "Descripción entidad",
    "Fecha del dato",
    "Código del dato",
    "Descripción del dato",
    "Valor",
]

# ---------- utilidades num/fecha ----------
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

# ---------- normalizador de encabezados ----------
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _norm_header(s: str) -> str:
    s = _strip_accents(str(s)).lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

# mapa de sinónimos normalizados -> nombre estándar
HEADER_MAP = {
    # Código de la entidad
    "codigo de entidad": "Código de entidad",
    "codigo entidad": "Código de entidad",
    "codigo de la entidad": "Código de entidad",
    "cod entidad": "Código de entidad",
    "n codent": "Código de entidad",
    "codent": "Código de entidad",

    # Descripción / nombre de la entidad
    "descripcion entidad": "Descripción entidad",
    "nombre de la entidad": "Descripción entidad",
    "nombre entidad": "Descripción entidad",
    "noment": "Descripción entidad",

    # Fecha (AAAAMM)
    "fecha del dato": "Fecha del dato",
    "fecha": "Fecha del dato",
    "c fecinf": "Fecha del dato",
    "fecinf": "Fecha del dato",
    "periodo": "Fecha del dato",
    "periodo aaamm": "Fecha del dato",
    "aaaamm": "Fecha del dato",
    "mes": "Fecha del dato",

    # Código de variable
    "codigo del dato": "Código del dato",
    "codigo dato": "Código del dato",
    "codigo partida": "Código del dato",
    "c partida": "Código del dato",
    "variable": "Código del dato",

    # Descripción de variable
    "descripcion del dato": "Descripción del dato",
    "descripcion dato": "Descripción del dato",
    "c descri2": "Descripción del dato",
    "descripcion": "Descripción del dato",

    # Valor
    "valor": "Valor",
    "n total": "Valor",
    "total": "Valor",
    "importe": "Valor",
    "valor actual": "Valor",
    "valor_actual": "Valor",
}

def _rename_headers(df: pd.DataFrame) -> pd.DataFrame:
    ren = {}
    for c in df.columns:
        nc = _norm_header(c)
        if nc in HEADER_MAP:
            ren[c] = HEADER_MAP[nc]
    if ren:
        df = df.rename(columns=ren)
    return df

# ---------- lector flexible ----------
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

# ---------- catálogo de variables ----------
def _build_var_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Var_label = SOLO descripción.
    Si una misma descripción corresponde a >1 código distinto,
    se numeran: 'Descripción', 'Descripción (2)', 'Descripción (3)', ...
    """
    pairs = df[["Var_desc", "Var_code"]].drop_duplicates()
    # cuántos códigos únicos por descripción
    counts = pairs.groupby("Var_desc")["Var_code"].nunique()
    dup_desc = set(counts[counts > 1].index)

    label_map = {}
    for desc, sub in pairs.groupby("Var_desc"):
        sub = sub.sort_values("Var_code")  # estable
        if desc in dup_desc:
            for i, (_, row) in enumerate(sub.iterrows(), start=1):
                label_map[(desc, row["Var_code"])] = f"{desc or '—'} ({i})"
        else:
            # único
            for _, row in sub.iterrows():
                label_map[(desc, row["Var_code"])] = desc or "—"

    df["Var_label"] = [label_map.get((d, c), d or "—") for d, c in zip(df["Var_desc"], df["Var_code"])]
    return df

# ---------- API pública ----------
@st.cache_data(show_spinner=True, ttl=600)
def load_df() -> pd.DataFrame:
    """
    Lee TODOS los .csv en ./data, intenta mapear encabezados "parecidos"
    a los nombres estándar y concatena sólo los que quedan completos.
    """
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    frames = []
    loaded, skipped = [], []

    for p in sorted(DATA_DIR.glob("*.csv")):
        try:
            raw = _read_csv_flexible(p)
            raw = _rename_headers(raw)
            missing = [c for c in COLS_STD if c not in raw.columns]
            if missing:
                skipped.append(f"{p.name} (faltan: {', '.join(missing)})")
                continue
            df = raw[COLS_STD].copy()
            df["__archivo__"] = p.name
            frames.append(df)
            loaded.append(p.name)
        except Exception as e:
            skipped.append(f"{p.name} (error: {e})")

    if not frames:
        st.caption("No se cargaron CSV válidos desde ./data")
        return pd.DataFrame(columns=COLS_STD + ["Fecha_dt","Mes","Valor_num","Entidad","Var_code","Var_desc","Var_label"])

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

    # Variables
    big["Var_code"] = big["Código del dato"].astype(str).str.strip()
    big["Var_desc"] = big["Descripción del dato"].astype(str).str.strip()

    # Etiquetas SOLO con descripción (con sufijos si hay duplicados)
    big = _build_var_labels(big)

    big = big.sort_values(["Fecha_dt", "Código de entidad", "Var_desc", "Var_code"]).reset_index(drop=True)

    # Info al usuario
    msg = f"Archivos cargados desde ./data: {len(loaded)}"
    if loaded:
        msg += " (" + ", ".join(loaded) + ")"
    if skipped:
        msg += f" · Ignorados: {len(skipped)}"
    st.caption(msg)
    if skipped:
        with st.expander("Ver archivos ignorados"):
            for s in skipped:
                st.markdown(f"- {s}")

    return big

def get_defaults(df: pd.DataFrame):
    """Entidad: la que contenga 'nación' si existe; Variable: la primera etiqueta (por descripción)."""
    ent_default = None
    if not df.empty:
        ents = df["Entidad"].unique().tolist()
        cand = [e for e in ents if "nacion" in e.lower() or "nación" in e.lower()]
        ent_default = cand[0] if cand else (ents[0] if ents else None)

    var_default_label = None
    if not df.empty:
        labs = df["Var_label"].unique().tolist()
        var_default_label = labs[0] if labs else None

    return ent_default, var_default_label

def month_options(df: pd.DataFrame):
    months = df.dropna(subset=["Mes"])["Mes"].unique().tolist()
    months = sorted(months)
    return months

def variable_catalog(df: pd.DataFrame) -> pd.DataFrame:
    """Catálogo único: etiqueta (sólo descripción) y su código asociado."""
    return df[["Var_label","Var_code"]].drop_duplicates().sort_values("Var_label")

def label_to_code(df: pd.DataFrame, label: str) -> str:
    """Convierte etiqueta (descripción o descripción con sufijo) a código."""
    cat = variable_catalog(df)
    row = cat.loc[cat["Var_label"] == label]
    if not row.empty:
        return row.iloc[0]["Var_code"]
    # fallback: si no encuentra, devuelve el mismo label
    return label
