from __future__ import annotations

from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.memory import parse_mem_csv, parse_mem_json
from src.app.services.sadf import convert_with_sadf


def load_mem_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-r",), prefer)
    if fmt == "json":
        return parse_mem_json(text), "json"
    else:
        return parse_mem_csv(text), "csv"


def render(path: str, prefer: Literal["auto", "12", "11"]) -> None:
    try:
        mdf, mfmt = load_mem_df(path, prefer)
        st.caption(f"Parsed as {mfmt}")
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"Memory read failed: {e}")
        return
    if mdf is not None and not mdf.empty:
        # Default metrics for memory
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
