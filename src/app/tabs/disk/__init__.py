from __future__ import annotations

from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.disk import parse_disk_csv, parse_disk_json
from src.app.parsers.filesystem import parse_fs_csv, parse_fs_json
from src.app.services.sadf import convert_with_sadf


def load_disk_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-d",), prefer)
    if fmt == "json":
        return parse_disk_json(text), "json"
    else:
        return parse_disk_csv(text), "csv"


def load_fs_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    fmt, text = convert_with_sadf(path, ("-F",), prefer)
    if fmt == "json":
        return parse_fs_json(text), "json"
    else:
        return parse_fs_csv(text), "csv"


def render(path: str, prefer: Literal["auto", "12", "11"]) -> None:
    try:
        ddf, dfmt = load_disk_df(path, prefer)
        st.caption(f"Parsed as {dfmt}")
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"Disk read failed: {e}")
        return

    if ddf is None or ddf.empty:
        st.info("No disk data")
        return

    devs = (
        sorted(
            pd.Series(ddf.get("dev", pd.Series(dtype=str))).dropna().astype(str).unique().tolist()
        )
        if "dev" in ddf.columns
        else []
    )
    sel_devs = st.multiselect("Devices", devs, default=devs[:2])

    tabs = st.tabs(["IOPS/Throughput", "Latency", "Utilization", "Capacity"])

    from .capacity import render as render_cap
    from .latency import render as render_lat
    from .throughput import render as render_thr
    from .utilization import render as render_utl

    with tabs[0]:
        render_thr(ddf, sel_devs)
    with tabs[1]:
        render_lat(ddf, sel_devs)
    with tabs[2]:
        render_utl(ddf, sel_devs)
    with tabs[3]:
        # Capacity uses filesystem data (-F)
        try:
            fsdf, _ = load_fs_df(path, prefer)
        except Exception as e:  # pragma: no cover - UI feedback
            st.error(f"Filesystem read failed: {e}")
            fsdf = None
        if fsdf is not None and not fsdf.empty:
            render_cap(fsdf)
        else:
            st.info("No filesystem data")

    st.download_button(
        "Download Disk CSV",
        ddf.to_csv(index=False).encode("utf-8"),
        file_name="disk.csv",
        mime="text/csv",
    )
