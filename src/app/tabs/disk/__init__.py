from __future__ import annotations

import os
from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.disk import parse_disk_csv, parse_disk_json
from src.app.parsers.filesystem import parse_fs_csv, parse_fs_json
from src.app.services.sadf import convert_with_sadf


def load_disk_df(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> tuple[pd.DataFrame, str]:
    if source == "csv":
        cp = os.path.join(csv_date_dir or "", "disk.csv")
        if not os.path.isfile(cp):
            raise FileNotFoundError("disk.csv not found under selected date directory")
        df = pd.read_csv(cp)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df, "csv"
    fmt, text = convert_with_sadf(path or "", ("-d",), prefer)
    if fmt == "json":
        return parse_disk_json(text), "json"
    else:
        return parse_disk_csv(text), "csv"


def load_fs_df(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> tuple[pd.DataFrame, str]:
    if source == "csv":
        cp = os.path.join(csv_date_dir or "", "fs.csv")
        if not os.path.isfile(cp):
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
        ddf, dfmt = load_disk_df(path, prefer, source, csv_date_dir)
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
            fsdf, _ = load_fs_df(path, prefer, source, csv_date_dir)
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
