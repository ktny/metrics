from __future__ import annotations

import os
from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.memory import parse_mem_csv, parse_mem_json
from src.app.services.sadf import convert_with_sadf


def _csv_path(csv_date_dir: str | None) -> str | None:
    if not csv_date_dir:
        return None
    p = os.path.join(csv_date_dir, "memory.csv")
    return p if os.path.isfile(p) else None


def load_mem_df(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> tuple[pd.DataFrame, str]:
    if source == "csv":
        cp = _csv_path(csv_date_dir)
        if not cp:
            raise FileNotFoundError("memory.csv not found under selected date directory")
        df = pd.read_csv(cp)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df, "csv"
    fmt, text = convert_with_sadf(path or "", ("-r",), prefer)
    if fmt == "json":
        return parse_mem_json(text), "json"
    else:
        return parse_mem_csv(text), "csv"


def render(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> None:
    try:
        mdf, mfmt = load_mem_df(path, prefer, source, csv_date_dir)
        st.caption(f"Parsed as {mfmt}")
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"Memory read failed: {e}")
        return
    if mdf is not None and not mdf.empty:
        choices = [
            c
            for c in ["memused_pct", "memfree", "avail", "cached", "buffers", "commit_pct"]
            if c in mdf.columns
        ]
        defaults = [mm for mm in ["memused_pct", "cached", "buffers"] if mm in choices]
        mem_metrics = st.multiselect("Metrics", choices, default=defaults)
        if mem_metrics:
            st.line_chart(mdf.set_index("timestamp")[mem_metrics])
        st.download_button(
            "Download Memory CSV",
            mdf.to_csv(index=False).encode("utf-8"),
            file_name="memory.csv",
            mime="text/csv",
        )
