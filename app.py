"""Pagina Streamlit: si sceglie una serie del file e se ne vede il grafico."""

from pathlib import Path

import pandas as pd
import streamlit as st

from loader import CleaningReport, DataLoadError, load_daily

DATA_FILE = Path(__file__).parent / "dati" / "set-dati.xlsx"


@st.cache_data
def load_data() -> tuple[pd.DataFrame, CleaningReport]:
    return load_daily(DATA_FILE)


st.set_page_config(page_title="Monitoraggio impianti", layout="wide")
st.title("Monitoraggio impianti")

try:
    data, report = load_data()
except DataLoadError as exc:
    st.error(str(exc))
    st.stop()

name = st.selectbox("Serie", data.columns)
series = data[name]
missing = f"{int(series.isna().sum())} valori mancanti in questa serie"

st.line_chart(series, x_label="Giorno", y_label=name)
st.caption(f"Periodo: {data.index.min():%d/%m/%Y} – {data.index.max():%d/%m/%Y} · {len(series)} giorni · {missing}")

with st.expander("Pulizia dei dati"):
    incomplete = ", ".join(f"{d:%d/%m/%Y}" for d in report.incomplete_days) or "nessuna"
    st.markdown(
        f"- Righe lette dal foglio: {report.rows_read}\n"
        f"- Giorni tenuti (una riga per giorno, quella delle 23:45): {report.days_kept}\n"
        f"- Righe scartate perché non delle 23:45: {report.rows_other_time}\n"
        f"- Righe scartate perché ripetute: {report.rows_duplicate}\n"
        f"- Date scartate perché senza riga delle 23:45: {incomplete}\n"
        f"- Valori mancanti in tutta la tabella: {report.missing_cells}"
    )
