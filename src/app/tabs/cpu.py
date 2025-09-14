from __future__ import annotations

import os
import re
from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.cpu import parse_cpu_csv, parse_cpu_json
from src.app.services.sadf import convert_with_sadf


def _csv_override(path: str) -> str | None:
    m = re.search(r"logs/(.+)/sa(\d{8})$", path)
    if not m:
        return None
    logs_dir = m.group(1)
    ymd = m.group(2)
    date_str = f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]}"
    candidate = os.path.join("logs", logs_dir, "csv", date_str, "cpu.csv")
    return candidate if os.path.isfile(candidate) else None


def load_cpu_df(path: str, prefer: Literal["auto", "12", "11"]) -> tuple[pd.DataFrame, str]:
    csv_path = _csv_override(path)
    if csv_path:
        df = pd.read_csv(csv_path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df, "csv-override"
    fmt, text = convert_with_sadf(path, ("-u", "-P", "ALL"), prefer)
    if fmt == "json":
        return parse_cpu_json(text), "json"
    else:
        return parse_cpu_csv(text), "csv"


def render(path: str, prefer: Literal["auto", "12", "11"]) -> None:
    try:
        df, fmt = load_cpu_df(path, prefer)
        st.caption(f"Parsed as {fmt}")
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"CPU load failed: {e}")
        return
    if df is not None and not df.empty:
        cpu_metrics = st.multiselect(
            "Metrics", ["user", "system", "iowait", "idle"], default=["user", "system", "idle"]
        )
        cpu_filter = st.text_input("CPU filter (e.g., all, 0, 1, 2)", value="all")
        wanted = [c.strip() for c in cpu_filter.split(",")] if cpu_filter else []
        if wanted and wanted != [""]:
            df = df[df["cpu"].isin(wanted)]
        series: dict[str, pd.Series] = {}
        cpus = sorted(pd.Series(df["cpu"]).astype(str).unique().tolist())
        for m in cpu_metrics:
            for cpu in cpus:
                key = f"{m}[{cpu}]"
                series[key] = df.loc[df["cpu"] == cpu].set_index("timestamp")[m]
        if series:
            chart_df = pd.concat(series, axis=1).sort_index()
            st.line_chart(chart_df)
        st.download_button(
            "Download CPU CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="cpu.csv",
            mime="text/csv",
        )
