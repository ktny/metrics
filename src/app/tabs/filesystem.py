from __future__ import annotations

import os
from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.filesystem import parse_fs_csv, parse_fs_json
from src.app.services.sadf import convert_with_sadf


def _csv_path(csv_date_dir: str | None) -> str | None:
    if not csv_date_dir:
        return None
    p = os.path.join(csv_date_dir, "fs.csv")
    return p if os.path.isfile(p) else None


def load_fs_df(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> tuple[pd.DataFrame, str]:
    if source == "csv":
        cp = _csv_path(csv_date_dir)
        if not cp:
            raise FileNotFoundError("fs.csv not found under selected date directory")
        df = pd.read_csv(cp)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df, "csv"
    fmt, text = convert_with_sadf(path or "", ("-F",), prefer)
    if fmt == "json":
        return parse_fs_json(text), "json"
    else:
        return parse_fs_csv(text), "csv"


def render(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> None:
    try:
        fsdf, fmt = load_fs_df(path, prefer, source, csv_date_dir)
        st.caption(f"Parsed as {fmt}")
    except Exception as e:  # pragma: no cover
        st.error(f"Filesystem read failed: {e}")
        return
    if fsdf is None or fsdf.empty:
        st.info("No filesystem data")
        return
    choices = [c for c in ["fsused_pct", "mb_free", "mb_used"] if c in fsdf.columns]
    defaults = [m for m in ["fsused_pct", "mb_free"] if m in choices]
    metrics = st.multiselect("Metrics", choices, default=defaults)
    if metrics:
        st.line_chart(fsdf.set_index("timestamp")[metrics])
    st.download_button(
        "Download FS CSV",
        fsdf.to_csv(index=False).encode("utf-8"),
        file_name="fs.csv",
        mime="text/csv",
    )

