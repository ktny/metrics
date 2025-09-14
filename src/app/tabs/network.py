from __future__ import annotations

import os
from typing import Literal

import pandas as pd
import streamlit as st

from src.app.parsers.network import parse_net_csv, parse_net_json
from src.app.services.sadf import convert_with_sadf


def _csv_path(csv_date_dir: str | None) -> str | None:
    if not csv_date_dir:
        return None
    p = os.path.join(csv_date_dir, "network.csv")
    return p if os.path.isfile(p) else None


def load_net_df(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> tuple[pd.DataFrame, str]:
    if source == "csv":
        cp = _csv_path(csv_date_dir)
        if not cp:
            raise FileNotFoundError("network.csv not found under selected date directory")
        df = pd.read_csv(cp)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df, "csv"
    fmt, text = convert_with_sadf(path or "", ("-n", "DEV"), prefer)
    if fmt == "json":
        return parse_net_json(text), "json"
    else:
        return parse_net_csv(text), "csv"


def render(
    path: str | None,
    prefer: Literal["auto", "12", "11"],
    source: Literal["sar", "csv"],
    csv_date_dir: str | None,
) -> None:
    try:
        ndf, nfmt = load_net_df(path, prefer, source, csv_date_dir)
        st.caption(f"Parsed as {nfmt}")
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"Network read failed: {e}")
        return

    if ndf is not None and not ndf.empty:
        ifaces = (
            sorted(pd.Series(ndf["iface"]).dropna().astype(str).unique().tolist())
            if "iface" in ndf.columns
            else []
        )
        sel_ifaces = st.multiselect("Interfaces", ifaces, default=ifaces[:2])
        net_metrics_all = [
            c for c in ["rxkB_s", "txkB_s", "rxpck_s", "txpck_s", "ifutil_pct"] if c in ndf.columns
        ]
        net_metrics = st.multiselect(
            "Metrics",
            net_metrics_all,
            default=[m for m in ["rxkB_s", "txkB_s"] if m in net_metrics_all],
        )
        if sel_ifaces and net_metrics:
            series: dict[str, pd.Series] = {}
            for m in net_metrics:
                for iface in sel_ifaces:
                    key = f"{m}[{iface}]"
                    series[key] = ndf.loc[ndf["iface"] == iface].set_index("timestamp")[m]
            if series:
                chart_df = pd.concat(series, axis=1).sort_index()
                st.line_chart(chart_df)
        st.download_button(
            "Download Network CSV",
            ndf.to_csv(index=False).encode("utf-8"),
            file_name="network.csv",
            mime="text/csv",
        )
